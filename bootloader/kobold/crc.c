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

#include <libopencm3/stm32/rcc.h>
#include <libopencm3/stm32/crc.h>

#include "crc.h"

int kobold_crc_run(void *data_)
{
	struct kobold_crc_data *data = data_;

	rcc_periph_clock_enable(RCC_CRC);
	CRC_INIT = 0xffffffff;
	CRC_POL = 0x04C11DB7;
	CRC_CR = CRC_CR_POLYSIZE_32 | CRC_CR_REV_IN_WORD | CRC_CR_REV_OUT;
	crc_reset();

	uint32_t *at = data->code_start;
	uint32_t crc = 0;
	for (uint32_t i = 0; i < data->header->length && at != data->code_end; at++, i += 4) {
		crc = crc_calculate((at != &data->header->crc && at != &data->header->length) ? *at : 0x00000000);
	}
	crc ^= 0xffffffff;
	return crc == data->header->crc ? KOBOLD_CRC_OUTCOME_PASS : KOBOLD_CRC_OUTCOME_FAIL;
}
