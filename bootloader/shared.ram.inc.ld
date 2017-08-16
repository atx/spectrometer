.kobold.ram ORIGIN(ram) : ALIGN(4) SUBALIGN(4)
{
	*(.kobold.ram.appctl);
} > ram
