/*
 * The MIT License (MIT)
 *
 * Copyright (C) 2016 Institute of Applied and Experimental Physics (http://www.utef.cvut.cz/)
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <ftdi.h>
#include <libusb.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <unistd.h>
#include <fcntl.h>

#include "utils.h"


int dm100_ac8reset(struct ftdi_context *ftdi)
{
	const uint8_t bitseq[][2] = {
		{ 0xff, 0x00 }, /* mode reset */
		{ 0x40, 0x20 }, /* AC8 = 0 */
		{ 0x44, 0x20 }, /* AC8 = 1 */
		{ 0x40, 0x20 }, /* AC8 = 0 */
		{ 0xff, 0x00 }  /* mode reset */
	};
	int i;
	int ret = 0;

	for (i = 0; i < ARRAY_SIZE(bitseq) && ret >= 0; i++) {
		ret = ftdi_set_bitmode(ftdi, bitseq[i][0], bitseq[i][1]);
		msleep(10);
	}

	return ret;
}

const uint8_t dm100_default_config[] = {
	140,
	0x04,

	128, /* LLD */
	0,
	129,
	0,
	130, /* ULD */
	0,
	131,
	0,

	132, /* hysteresis */
	0,
	133, /* clkmux */
	0,

	134, /* pretrig */
	0,
	135,
	0,
	136, /* count */
	0,
	137,
	0,
	138, /* posttrig */
	0,
	139,
	0,

	142, /* gothr, ..., trig cfg, gate cfg */
	0x80,

	143, /* add..., stres cfg, disc cfg, bus8 */
	0x01
};

static const char *dm100_descs[] = {
	"Single Compact FAST ADC",
	"Single FAST ADC Interface",
	NULL
};

int dm100_connect(struct ftdi_context *ftdi)
{
	int ret;

	ftdi_init(ftdi);

	/* TODO: Be a bit more selective and support multiple devices properly */
	ret = open_by_desc_prefix(ftdi, 0x0403, 0x6014, dm100_descs);
	if (ret < 0) {
		perror("Failed to open the device");
		return ret;
	}
	ftdi_usb_purge_buffers(ftdi);

	dm100_ac8reset(ftdi);

	/* Initialize synchronous communication */
	ret = ftdi_set_latency_timer(ftdi, 2);
	if (ret < 0) {
		perror("Failed to set the latency timer");
		goto close;
	}
	ret = ftdi_read_data_set_chunksize(ftdi, 0x10000);
	if (ret < 0) {
		perror("Failed to set read data chunksize");
		goto close;
	}
	ret = ftdi_write_data_set_chunksize(ftdi, 0x10000);
	if (ret < 0) {
		perror("Failed to write read data chunksize");
		goto close;
	}
	ret = ftdi_setflowctrl(ftdi, SIO_RTS_CTS_HS);
	if (ret < 0) {
		perror("Failed to set flow control");
		goto close;
	}
	msleep(20);
	ret = ftdi_set_bitmode(ftdi, 0xff, 0x00);
	if (ret < 0) {
		perror("Failed to set bitmode 0x00");
		goto close;
	}
	msleep(20);
	ftdi_set_bitmode(ftdi, 0xff, 0x40);
	if (ret < 0) {
		perror("Failed to set bitmode 0x40");
		goto close;
	}

	ret = ftdi_write_data(ftdi, dm100_default_config, sizeof(dm100_default_config));
	if (ret < 0) {
		perror("ftdi write failed");
		goto close;
	}
	msleep(300);
	ftdi_usb_purge_buffers(ftdi);

	return 0;

close:
	ftdi_usb_close(ftdi);
	ftdi_deinit(ftdi);

	return ret;
}

int main(int argc, char *argv[])
{
	struct ftdi_context ftdi;
	int ret;

	ret = dm100_connect(&ftdi);
	if (ret < 0) {
		perror("dm100_connect failed");
		exit(EXIT_FAILURE);
	}

	enter_rw_loop(&ftdi);

	//epollfd = epoll_create1(0);
	//ev.events = EPOLLIN;
	//ev.data.fd = fileno(stdin);
	//epoll_ctl(epollfd, EPOLL_CTL_ADD, fileno(stdin), &ev);
	//fcntl(fileno(stdin), F_SETFL, O_NONBLOCK);

	//while (true) {
	//	ret = ftdi_read_data(&ftdi, buf, sizeof(buf));
	//	if (ret > 0) {
	//		write(fileno(stdout), buf, ret);
	//		fflush(stdout);
	//	}
	//	/* TODO: Figure out how how to handle EOF in epoll */
	//	ret = epoll_wait(epollfd, events, ARRAY_SIZE(events), 100);
	//	if (ret > 0) {
	//		ret = fread(buf, 1, sizeof(buf), stdin);
	//		if (ret > 0)
	//			ftdi_write_data(&ftdi, buf, ret);
	//	} else if (ret < 0) {
	//		break;
	//	}
	//	if (feof(stdin))
	//		break;
	//}
}
