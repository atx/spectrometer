/* 
 * Copyright (C) 2015 Josef Gajdusek
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

extern int _vectors_flash_start;
extern int _vectors_start;
extern int _vectors_end;
extern int _data_flash_start;
extern int _data_start;
extern int _data_end;
extern int _bss_start;
extern int _bss_end;

/* for _sbrk */
int end;

__attribute__((section(".stack"), used))
static char stack[1024]; /* 1kiB of stack space */

int main(void);

void reset_handler()
{
	int *from = &_data_flash_start;
	int *to = &_data_start;

	while (to != &_data_end)
		*(to++) = *(from++);

	to = &_bss_start;
	while (to != &_bss_end)
		*(to++) = 0;

	main();
	while (1) {}
}
