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

#include <stdlib.h>
#include <stdint.h>
#include <stdio.h>
#include <libopencm3/cm3/common.h>
#include <libopencm3/cm3/scb.h>
#include <libopencm3/cm3/nvic.h>
#include <libopencm3/cm3/systick.h>
#include <libopencm3/cm3/cortex.h>
#include <libopencm3/stm32/f3/rcc.h>
#include <libopencm3/stm32/adc.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/usb/usbd.h>
#include <libopencm3/usb/cdc.h>
#include <libopencm3/stm32/f3/syscfg.h>
#include <libopencm3/stm32/f3/flash.h>

#include "acq.h"
#include "bias.h"
#include "cdc.h"
#include "log.h"

static void rcc_init()
{
	rcc_osc_bypass_enable(RCC_HSE);
	rcc_osc_on(RCC_HSE); /* HSE = 12MHz */
	rcc_wait_for_osc_ready(RCC_HSE);

	rcc_set_hpre(RCC_CFGR_HPRE_DIV_NONE); /* AHB = 72MHz (72MHz)*/
	rcc_set_ppre1(RCC_CFGR_PPRE1_DIV_2); /* APB1 = 36MHz (36MHz)*/
	rcc_set_ppre2(RCC_CFGR_PPRE2_DIV_NONE); /* APB2 = 72MHz (72MHz) */

	flash_set_ws(FLASH_ACR_LATENCY_2WS);

	/* SYSCLK = PLLCLK = HSE * 9 = 72 */
	rcc_set_pll_multiplier(RCC_CFGR_PLLMUL_PLL_IN_CLK_X6);
	rcc_set_pll_source(RCC_CFGR_PLLSRC_HSE_PREDIV);

	/* USBCLK = PLLCLK / 1.5 = 48MHz*/
	rcc_usb_prescale_1_5();

	rcc_osc_on(RCC_PLL);
	rcc_wait_for_osc_ready(RCC_PLL);

	rcc_set_sysclk_source(RCC_CFGR_SW_PLL);

	rcc_ahb_frequency = 72000000;
	rcc_apb1_frequency = 36000000;
	rcc_apb2_frequency = 72000000;
}

static void init()
{
	cm_disable_interrupts();

	/* 1 priority, 16 subpriorities (-> no interrupt preemption)*/
	scb_set_priority_grouping(SCB_AIRCR_PRIGROUP_NOGROUP_SUB16);

	rcc_init();

	rcc_periph_clock_enable(RCC_GPIOA);
	rcc_periph_clock_enable(RCC_GPIOB);
	rcc_periph_clock_enable(RCC_GPIOF);

	log_init();
	bias_init();
	cdc_init();
	acq_init();

	cm_enable_interrupts();
}

int main(void)
{
	// TODO: The USB connection seems to be interfering with my debugger for some reason, figure out why
	// This waits for about a second to make it easier to connnect
	for (volatile int i = 0; i < 1000000; i++);

	init();

	log("Initialized\n");

	while (true) {
		__asm__("wfi");
	}
}
