
#include "kobold.h"

#include <stdbool.h>

void kobold_main(const struct kobold_bootloader *bld) {
	const struct kobold_module *at = bld->root;
	while (true) {
		int outcome = at->run(at->data);
		at = at->outcomes[outcome];
	}
}
