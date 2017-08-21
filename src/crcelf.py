#! /usr/bin/env python3

import argparse
import zlib
import lief
import struct


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("elf")
    parser.add_argument("-s", "--symbol-name", required=True)
    parser.add_argument("-b", "--bin-file", required=True)
    args = parser.parse_args()

    elf = lief.parse(args.elf)

    def symbol_by_name(name):
        return next(filter(lambda x: x.name == name,
                           elf.static_symbols))

    crc_symbol = symbol_by_name(args.symbol_name)

    with open(args.bin_file, "rb") as f:
        data = f.read()
        crc_value = zlib.crc32(data)

    assert len(data) % 4 == 0, "Code length not aligned to 4 byte boundary"

    elf.patch_address(crc_symbol.value,
                      struct.pack("<II", crc_value, len(data)))

    elf.write(args.elf)
