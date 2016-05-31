#! /usr/bin/env python3

import serial.aio
import time
import asyncio
import sys

if len(sys.argv) < 2:
    print("Usage: ./acmspeed.py <portname>")
    sys.exit(1)

class Speedometer(asyncio.Protocol):

    def __init__(self):
        self._cnt = 0

    @asyncio.coroutine
    def print_start(self):
        sleeptime = 0.5
        while True:
            yield from asyncio.sleep(sleeptime)
            speed = self._cnt / sleeptime
            unit = ""
            if speed > 1000:
                unit = "k"
                speed /= 1000
            print("\r%.2f %sB/s         " % (speed, unit), end = "", flush = True)
            self._cnt = 0

    def connection_made(self, transport):
        asyncio.ensure_future(self.print_start())

    def data_received(self, data):
        self._cnt += len(data)

evloop = asyncio.get_event_loop()
coro = serial.aio.create_serial_connection(evloop, Speedometer, sys.argv[1])
evloop.run_until_complete(coro)
evloop.run_forever()
evloop.close()
