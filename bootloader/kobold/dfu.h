/* 
 * Copyright (C) 2017 Institute of Applied and Experimental Physics (http://www.utef.cvut.cz/)
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
