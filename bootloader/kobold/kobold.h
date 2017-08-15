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

#ifndef KOBOLD_H
#define KOBOLD_H

#define KOBOLD_MODULE_NAME_MAX		8

struct kobold_module {
	void *data;
	int (*run)(void *data);
	const struct kobold_module *outcomes[];
};

struct kobold_bootloader {
	const struct kobold_module *root;
};

void kobold_main(const struct kobold_bootloader *bld);

#endif
