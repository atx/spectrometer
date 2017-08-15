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

#include <libopencm3/cm3/nvic.h>
#include <libopencm3/cm3/scb.h>
#include <libopencm3/cm3/vector.h>
#include "boot_m3.h"

__attribute__((noinline))
static void run(void *stack_address, void *reset_address)
{
	asm volatile (
		"mov sp, %0\n" :: "r" (stack_address)
	);
	asm volatile (
		"mov pc, %0\n" :: "r" (reset_address)
	);
}

int kobold_boot_m3_run(void *data_)
{
	struct kobold_boot_m3_data *data = data_;
	SCB_VTOR = (uint32_t)data->application;
	vector_table_t *vectors = data->application;
	void *stack_address = vectors->initial_sp_value;
	void *reset_address = vectors->reset;
	run(stack_address, reset_address);
	return 0;
}
