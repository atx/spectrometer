
#ifndef _UTILS_H_
#define _UTILS_H_

#include <fcntl.h>
#include <ftdi.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/epoll.h>

#define ARRAY_SIZE(x) (sizeof(x) / sizeof(x[0]))
#define msleep(x) usleep((x) * 1000)

static inline int open_by_desc_prefix(struct ftdi_context *ftdi,
									   uint16_t vid, uint16_t pid,
									   const char **descs)
{
	struct ftdi_device_list *list = NULL;
	char manuf[100];
	char desc[100];
	char ser[100];
	char *sub;
	bool match = false;
	int ret;
	int i;

	ret = ftdi_usb_find_all(ftdi, &list, vid, pid);
	if (ret < 0) {
		perror("Failed to enumerate devices");
		return ret;
	}

	if (list == NULL)
		return -1;

	do {
		ftdi_usb_get_strings(ftdi, list->dev,
							 manuf, sizeof(manuf),
							 desc, sizeof(desc),
							 ser, sizeof(ser));
		for (i = 0; descs[i] != NULL; i++) {
			sub = strstr(desc, descs[i]);
			if (sub == desc) {
				match = true;
				break;
			}
		}
	} while (!match && (list = list->next));

	return match ? ftdi_usb_open_dev(ftdi, list->dev) : -1;
}

static inline void enter_rw_loop(struct ftdi_context *ftdi)
{
	uint8_t buf[10000];
	int ret;

	fcntl(fileno(stdin), F_SETFL, O_NONBLOCK);

	while (true) {
		/* TODO: Rewrite this loop so that it uses epoll on both read and writes.
		 * This should be possible by using libusb directly.
		 * */
		ret = ftdi_read_data(ftdi, buf, sizeof(buf));
		if (ret > 0) {
			fwrite(buf, 1, ret, stdout);
			fflush(stdout);
		}
		ret = 1;
		if (ret > 0) {
			ret = fread(buf, 1, sizeof(buf), stdin);
			if (ret > 0)
				ftdi_write_data(ftdi, buf, ret);
		} else if (ret < 0) {
			break;
		}
		if (feof(stdin))
			break;
	}
}

#endif
