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

#ifndef KOBOLD_CRC_H
#define KOBOLD_CRC_H

#include <stdint.h>

struct kobold_crc_header {
	uint32_t crc;
	uint32_t length;
};

struct kobold_crc_data {
	struct kobold_crc_header *header;
	void *code_start;
	void *code_end;
};

enum kobold_crc_outcome {
	KOBOLD_CRC_OUTCOME_PASS = 0,
	KOBOLD_CRC_OUTCOME_FAIL = 1,
};

int kobold_crc_run(void *data);

#endif
