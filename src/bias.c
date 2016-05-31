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

#include "bias.h"

#include <libopencm3/stm32/gpio.h>

#define BIAS_BANK	GPIOA
#define BIAS_GPIO	GPIO8

static bool bias_enabled = false;

void bias_init()
{
	gpio_mode_setup(BIAS_BANK, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, BIAS_GPIO);
	bias_disable();
}

void bias_enable()
{
	bias_enabled = true;
	gpio_set(BIAS_BANK, BIAS_GPIO);
}

void bias_disable()
{
	bias_enabled = false;
	gpio_clear(BIAS_BANK, BIAS_GPIO);
}

bool bias_isenabled()
{
	return bias_enabled;
}
