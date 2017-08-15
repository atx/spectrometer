

#ifndef KOBOLD_DFU_H
#define KOBOLD_DFU_H

#include <stdint.h>

enum kobold_dfu_outcome {
	KOBOLD_DFU_OUTCOME_DONE = 0,
};

struct kobold_dfu_data {
	void (*init)(void);
	const char *usb_strings[4];
};

int kobold_dfu_run(void *data);

#endif
