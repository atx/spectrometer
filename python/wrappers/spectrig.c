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

static const char *spectrig_descs[] = {
	"Spectrig LT V1.0.0 sn:",
	"SFITPIX 3.0 Parallel sn:",
	NULL
};

int spectrig_connect(struct ftdi_context *ftdi)
{
	int ret;

	ftdi_init(ftdi);

	/* TODO: Be a bit more selective and support multiple devices properly */
	ret = open_by_desc_prefix(ftdi, 0x0403, 0x6010, spectrig_descs);
	if (ret < 0) {
		perror("Failed to open the device");
		return ret;
	}
	ftdi_usb_purge_buffers(ftdi);

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

	ret = spectrig_connect(&ftdi);
	if (ret < 0) {
		perror("spectrig_connect failed");
		exit(EXIT_FAILURE);
	}

	enter_rw_loop(&ftdi);
}
