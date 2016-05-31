#! /usr/bin/env python3

import argparse
from spectrometer import HistFile

parser = argparse.ArgumentParser(
    "Parse histogram file, threshold and show CPM"
)

parser.add_argument(
    "file",
    help = "Histogram filename",
    nargs = "+"
)

parser.add_argument(
    "-t", "--threshold",
    help = "Threshold to apply",
    type = int,
    required = True
)

args = parser.parse_args()

for fname in args.file:
    hfil = HistFile.load_file(fname)
    cnt = sum(hfil.vals[i] for i in range(args.threshold, len(hfil.vals)))
    print("%.4f" % (cnt / (hfil.to - hfil.from_).seconds * 60))


