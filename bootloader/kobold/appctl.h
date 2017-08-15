
#ifndef KOBOLD_APPCTL_H
#define KOBOLD_APPCTL_H

#include <stdint.h>

#define KOBOLD_APPCTL_MAGIC		0xdeadcafe

enum kobold_appctl_outcome {
	KOBOLD_APPCTL_OUTCOME_CONTINUE = 0,
	KOBOLD_APPCTL_OUTCOME_FLASH = 1,
};

struct kobold_appctl_data {
	uint32_t magic;
};

int kobold_appctl_run(void *data);

#endif
