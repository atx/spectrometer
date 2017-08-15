
#ifndef KOBOLD_BOOT_M3
#define KOBOLD_BOOT_M3

struct kobold_boot_m3_data {
	void *application;
};

int kobold_boot_m3_run(void *data);

#endif
