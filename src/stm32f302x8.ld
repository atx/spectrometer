/*
 * Linker script for STM32F302x8
 * */

MEMORY
{
	flash (RX)  : org = 0x08000000, len = 64k
	ram   (RWX) : org = 0x20000000, len = 16k
}

EXTERN(vector_table)

ENTRY(reset_handler)

SECTIONS
{
	.vectors ORIGIN(flash) : ALIGN(256)
	{
		KEEP(*(.vectors));
	} > flash

	.text : ALIGN(16) SUBALIGN(16)
	{
		_text_start = .;
		*(.text)
		*(.text.*)
		*(.rodata)
		*(.rodata.*)
		*(.gcc*)
		_text_end = .;
	} > flash

	_data_flash_start = _text_end;

	.stack ORIGIN(ram) : ALIGN(4) SUBALIGN(4)
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
	} > ram AT > flash

	.bss : ALIGN(4) SUBALIGN(4)
	{
		_bss_start = .;
		*(.bss)
		*(.bss.*)
		*(COMMON)
		_bss_end = .;
	} > ram
}
