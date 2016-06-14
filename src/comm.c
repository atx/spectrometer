/* 
 * Copyright (C) 2016 Institute of Applied and Experimental Physics (http://www.utef.cvut.cz/)
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.*
 */

#include <limits.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "acq.h"
#include "bias.h"
#include "cdc.h"
#include "comm.h"
#include "utils.h"

#define FIRMWARE_VERSION	2

enum packet_type {
	/* Host -> Device */
	PACKET_NOP		= 0x01,
	PACKET_PING		= 0x02,
	PACKET_GET		= 0x03,
	PACKET_SET		= 0x04,
	PACKET_START	= 0x05,
	PACKET_END		= 0x06,

	/* Device -> Host */
	PACKET_PONG		= 0x82,
	PACKET_GETRESP	= 0x83,
	PACKET_EVENT	= 0x87,
	PACKET_WAVE		= 0x88,
	PACKET_ERROR    = 0xff,
};

enum error {
	EUNKNOWN	= 1,
	EINKEY		= 2,
	EINOP		= 3,
};

uint32_t comm_missed = 0;

static inline void comm_send(char *buf, size_t len, bool flush)
{
	if (!cdc_send(buf, len))
		comm_missed++;
	else if (flush)
		cdc_flush();
}

static inline void comm_send_error(enum error errno)
{
	char p[] = { PACKET_ERROR, errno };
	comm_send(p, sizeof(p), true);
}

void comm_send_event(uint16_t val)
{
	char p[] = { PACKET_EVENT, LOBYTE(val), HIBYTE(val) };
	comm_send(p, sizeof(p), false);
	cdc_flush();
}

void comm_send_wave(uint16_t *vals, int len)
{
	char p[len * sizeof(*vals) + 2];
	int i;

	p[0] = PACKET_WAVE;
	p[1] = len & 0xff;

	for (i = 0; i < len; i++) {
		p[2 + i * 2 + 0] = HIBYTE(vals[i]);
		p[2 + i * 2 + 1] = LOBYTE(vals[i]);
	}

	comm_send(p, sizeof(p), false);
}

/* Handlers return the amount of bytes taken or negative value in case of failure
 * */
static int comm_cb_nop(char *buf, int len)
{
	(void)buf;
	(void)len;
	/* We do nothing, surprise! */
	return 1;
}

static int comm_cb_ping(char *buf, int len)
{
	(void)buf;
	(void)len;
	char p[] = { PACKET_PONG };
	comm_send(p, sizeof(p), true);
	return 1;
}

enum propkey {
	CONF_FW		= 0x01,
	CONF_THRESH	= 0x02,
	CONF_BIAS	= 0x03,
	CONF_AMP	= 0x04,
	CONF_RTHRESH = 0x05,
	CONF_SERNO	= 0x06
};

struct propvar {
	enum propkey key;
	void (*get)(const struct propvar *prop);
	void (*set)(const struct propvar *prop, char *buf, int len);
	int len;
	void *data;
};

static void comm_const_uint16_get(const struct propvar *prop)
{
	uint16_t data = ((uint32_t) prop->data) & 0xffff;
	char p[] =
		{ PACKET_GETRESP, prop->key, LOBYTE(data), HIBYTE(data)};
	comm_send(p, sizeof(p), true);
}

static void comm_uint16_set(const struct propvar *prop, char *buf, int len)
{
	UNUSED(len);
	uint16_t *i = prop->data;
	*i = le_to_u16(&buf[2]);
}

static void comm_uint16_get(const struct propvar *prop)
{
	int16_t *i = prop->data;
	char p[] =
		{ PACKET_GETRESP, prop->key,
			BYTE(0, *i),
			BYTE(1, *i)};
	comm_send(p, sizeof(p), true);
}

struct boolprop {
	void (*enable)();
	void (*disable)();
	bool (*isenabled)();
};

static void comm_boolprop_get(const struct propvar *prop)
{
	struct boolprop *bl = prop->data;
	char p[] =
		{ PACKET_GETRESP, prop->key,
			bl->isenabled() ? 0x01 : 0x00 };

	comm_send(p, sizeof(p), true);
}

static void comm_boolprop_set(const struct propvar *prop, char *buf, int len)
{
	UNUSED(prop);
	UNUSED(len);

	struct boolprop *bl = prop->data;

	if (buf[2] & 0x01)
		bl->enable();
	else
		bl->disable();
}

static struct boolprop boolprop_bias = {
	.enable = bias_enable,
	.disable = bias_disable,
	.isenabled = bias_isenabled,
};

static struct boolprop boolprop_amp = {
	.enable = acq_amp_enable,
	.disable = acq_amp_disable,
	.isenabled = acq_amp_isenabled,
};

static const struct propvar propvars[] = {
	{ CONF_FW, comm_const_uint16_get, NULL, 2, (void *)FIRMWARE_VERSION },
	{ CONF_THRESH, comm_uint16_get, comm_uint16_set, 2, &acq_channel.threshold },
	{ CONF_BIAS, comm_boolprop_get, comm_boolprop_set, 1, &boolprop_bias },
	{ CONF_AMP, comm_boolprop_get, comm_boolprop_set, 1, &boolprop_amp },
	{ CONF_RTHRESH, comm_uint16_get, comm_uint16_set, 2, &acq_channel.rthresh },
	{ CONF_SERNO, comm_const_uint16_get, NULL, 2, (void *)SERNO }
};

static const struct propvar *comm_resolve_key(enum propkey k)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(propvars); i++)
		if (propvars[i].key == k)
			return &propvars[i];

	return NULL;
}

static int comm_cb_get(char *buf, int len)
{
	const struct propvar *p;

	if (len < 2)
		return 0;

	p = comm_resolve_key(buf[1]);

	if (p == NULL)
		comm_send_error(EINKEY);
	else if (p->get == NULL)
		comm_send_error(EINOP);
	else
		p->get(p);

	return 2;
}

static int comm_cb_set(char *buf, int len)
{
	const struct propvar *p;

	if (len < 2)
		return 0;

	p = comm_resolve_key(buf[1]);

	if (p == NULL)
		comm_send_error(EINKEY);
	else if (p->set == NULL)
		// TODO: Note that this will probably produce some garbage bytes
		comm_send_error(EINOP);
	else if (len - 2 < p->len)
		return 0;
	else
		p->set(p, buf, len);

	return 2 + p->len;
}

static int comm_cb_start(char *buf, int len)
{
	(void)buf;
	(void)len;
	acq_start();
	return 1;
}

static int comm_cb_end(char *buf, int len)
{
	(void)buf;
	(void)len;
	acq_pause();
	return 1;
}

struct callback {
	int (*fn)(char *buf, int len);
	enum packet_type type;
};

static const struct callback callbacks[] = {
	{ comm_cb_nop,	PACKET_NOP },
	{ comm_cb_ping,	PACKET_PING },
	{ comm_cb_get,  PACKET_GET },
	{ comm_cb_set,	PACKET_SET },
	{ comm_cb_start,  PACKET_START },
	{ comm_cb_end,    PACKET_END },
};

void comm_push_rx(char *new, int len)
{
	static char buff[64];
	static size_t buff_len = 0;
	bool matched;
	int copied = 0;
	unsigned int i;
	int ret;

	do {
		if (copied < len && buff_len < sizeof(buff)) {
			i = min((unsigned int)len - copied, sizeof(buff) - buff_len);
			memcpy(&buff[buff_len], &new[copied], i);
			copied += i;
			buff_len += i;
		}
		matched = false;
		for (i = 0; i < ARRAY_SIZE(callbacks); i++)
			if (buff[0] == callbacks[i].type) {
				matched = true;
				ret = callbacks[i].fn(buff, buff_len);
				break;
			}
		if (!matched) {
			/* Garbage byte, should not happen */
			ret = 1;
		}
		if (ret) {
			buff_len -= ret;
			memmove(buff, &buff[ret], buff_len);
		}
		if (ret == 0 && buff_len == sizeof(buff)) {
			/* This should never happen, increase size of buff if it does */
			buff_len = 0;
		}
	} while (buff_len > 0 && ret != 0);
}
