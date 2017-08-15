
#ifndef KOBOLD_H
#define KOBOLD_H

#define KOBOLD_MODULE_NAME_MAX		8

struct kobold_module {
	void *data;
	int (*run)(void *data);
	const struct kobold_module *outcomes[];
};

struct kobold_bootloader {
	const struct kobold_module *root;
};

void kobold_main(const struct kobold_bootloader *bld);

#endif
