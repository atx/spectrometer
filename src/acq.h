/* 
 * Copyright (C) 2016 Institute of Applied and Experimental Physics (http://www.utef.cvut.cz/)
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

#ifndef ACQ_H
#define ACQ_H

#include "comm.h"
#include <stdint.h>
#include <stdbool.h>

void acq_init();

bool acq_amp_isenabled();
void acq_amp_enable();
void acq_amp_disable();

void acq_start();
void acq_pause();

#define BUFFER_SIZE		1000

struct acq_state {
	uint16_t threshold;
	uint16_t max;
	uint16_t rthresh;
	int falling;
	bool pulse;
	bool mute;
	uint16_t buff[BUFFER_SIZE];
};

#define CHANNEL_COUNT				2

extern struct acq_state acq_channel;

#endif
