/*
 * Linker script for STM32F302x8
 * */

INCLUDE ../shared/stm32f302x8.memory.inc.ld

EXTERN(vector_table)

ENTRY(reset_handler)

SECTIONS
{
	.vectors ORIGIN(flash_app) : ALIGN(256)
	{
		KEEP(*(.vectors));
	} > flash_app

	.kobold.flash : ALIGN(4) SUBALIGN(4)
	{
		INCLUDE ../shared/shared.flash.inc.ld
	} > flash_app

	.text : ALIGN(16) SUBALIGN(16)
	{
		_text_start = .;
		*(.text)
		*(.text.*)
		*(.rodata)
		*(.rodata.*)
		*(.gcc*)
		_text_end = .;
	} > flash_app

	_data_flash_start = _text_end;

	INCLUDE ../shared/shared.ram.inc.ld

	.stack (NOLOAD) : ALIGN(4) SUBALIGN(4)
	{
		_stack_start = .;
		KEEP(*(.stack));
		_stack = .;
	} > ram

	.data : ALIGN(4) SUBALIGN(4)
	{
		_data_start = .;
		*(.data)
		*(.data.*)
		*(.ramtext)
		*(.ramfuncs)
		_data_end = .;
	} > ram AT > flash_app

	.bss : ALIGN(4) SUBALIGN(4)
	{
		_bss_start = .;
		*(.bss)
		*(.bss.*)
		*(COMMON)
		_bss_end = .;
	} > ram

	_flash_app_start = ORIGIN(flash_app);
	_flash_app_stop = ORIGIN(flash_app) + LENGTH(flash_app);
}
