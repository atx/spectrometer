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

#include <libopencm3/cm3/common.h>
#include <libopencm3/stm32/f3/rcc.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/f3/flash.h>

#include "kobold/kobold.h"
#include "kobold/appctl.h"
#include "kobold/boot_m3.h"
#include "kobold/crc.h"
#include "kobold/dfu.h"

extern int _flash_app_start;

static struct kobold_boot_m3_data boot_m3_data = {
	.application = &_flash_app_start,
};

static const struct kobold_module module_boot = {
	.data = &boot_m3_data,
	.run = kobold_boot_m3_run
};

static void dfu_init()
{
	// TODO: Share with application code?
	rcc_osc_bypass_enable(RCC_HSE);
	rcc_osc_on(RCC_HSE);
	rcc_wait_for_osc_ready(RCC_HSE);

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

	rcc_periph_clock_enable(RCC_GPIOA);

	gpio_mode_setup(GPIOA, GPIO_MODE_OUTPUT, GPIO_PUPD_NONE, GPIO9);
	gpio_mode_setup(GPIOA, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO11 | GPIO12);
	gpio_set_af(GPIOA, GPIO_AF14, GPIO11 | GPIO12);

	gpio_clear(GPIOA, GPIO9);
	gpio_set(GPIOA, GPIO9);
}

static struct kobold_dfu_data dfu_data = {
	.init = dfu_init,
	.usb_strings = {
		"IEAP CTU",
		"Spectrometer Acquisition Board (DFU)",
		"DFU",
		/* For dfu-util: 6 2k pages of read-only for bootloader, 26 2k pages for application */
		"@Internal Flash   /0x08000000/6*002Ka,26*002Kg",
	}
};

static const struct kobold_module module_dfu = {
	.data = &dfu_data,
	.run = kobold_dfu_run,
	.outcomes = {
		[KOBOLD_DFU_OUTCOME_DONE] = &module_boot
	}

};

extern struct kobold_appctl_data kobold_appctl;

static const struct kobold_module module_appctl = {
	.data = &kobold_appctl,
	.run = kobold_appctl_run,
	.outcomes = {
		[KOBOLD_APPCTL_OUTCOME_CONTINUE] = &module_boot,
		[KOBOLD_APPCTL_OUTCOME_FLASH] = &module_dfu,
	}
};

static const struct kobold_bootloader bootloader = {
	.root = &module_appctl
};

int main() {
	kobold_main(&bootloader);
}
