/*
 * Memory layout definition for STM32F302x8
 * */

MEMORY
{
	flash_bootloader (RX) : org = 0x08000000, len = 12k /* For completeness */
	flash_app (RX)  : org = 0x08003000, len = 52k
	ram   (RWX) : org = 0x20000000, len = 16k
}
