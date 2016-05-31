#! /usr/bin/env python3.5
# The MIT License (MIT)
#
# Copyright (C) 2016 Institute of Applied and Experimental Physics (http://www.utef.cvut.cz/)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import argparse
import asyncio
import base64
import concurrent
import datetime
import glob
import http
import json
import os
import random
import socketserver
import sys
import threading
import time
import traceback
import weakref
import webbrowser
from aiohttp import web
from http import server
from spectrometer import *

parser = argparse.ArgumentParser(
    prog = "Spectrometer GUI"
)
parser.add_argument(
    "-s", "--serial",
    help = "Serial port to use",
    default = "/dev/ttyACM*"
)
parser.add_argument(
    "-t", "--type",
    help = "Spectrometer type",
    choices = ["dummy", "serial", "sipos"],
    default = "serial"
)
parser.add_argument(
    "-b", "--bind",
    help = "Address to bind to",
    default = "127.0.0.1"
)
parser.add_argument(
    "-l", "--log",
    help = "Log timestamped events into a file",
    default = None
)

args = parser.parse_args()

THRESHOLD = 100

def spectrometer_connect():
    if args.type == "dummy":
        spect = DummySpectrometer(period = 0.001, chans = 4096)
    elif args.type == "serial":
        spect = SerSpect(glob.glob(args.serial)[0])
        spect.set_prop(spect.PROP_THRESH, THRESHOLD)
        assert spect.get_prop(spect.PROP_THRESH) == THRESHOLD
    elif args.type == "sipos":
        spect = SIPOSSpectrometer(glob.glob(args.serial)[0])
    spect.start()
    return spect

spectrometer = spectrometer_connect()

csrf_token = base64.b64encode(os.urandom(20)).decode()

# WebSockets are not constrained by Same-Origin policy, this gets sent by the
# client to configure and authenticate itself.
metadata_json = json.dumps({"csrf": csrf_token,
                            "channels": spectrometer.channels,
                            "driver": spectrometer.__class__.__name__,
                            "fw_version": spectrometer.fw_version}
                           ).encode()

class Master:

    def __init__(self, spectrometer, logfile = None):
        self.spectrometer = spectrometer
        self.clients = []
        self.history = [10] * spectrometer.channels
        self.since = time.time()
        self.logfile = logfile

    def clear(self):
        self.history = [0] * self.spectrometer.channels
        self.since = time.time()
        [c.send_history(self.history, self.since) for c in self.clients]

    async def spectrometer_loop(self):
        self.clear()
        # Leak here
        fil = open(self.logfile, "w+") if self.logfile else None
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as e:
            while True:
                v = await asyncio.get_event_loop().run_in_executor(e, self.spectrometer.next_event)
                if v >= len(self.history):
                    continue
                self.history[v] += 1
                if fil:
                    fil.write("%s %d\n" % (datetime.datetime.now().isoformat()[:-7], v))
                    fil.flush()
                self.broadcast_event(v)

    def broadcast(self, jsn):
        [c.send(jsn) for c in self.clients]

    def broadcast_history(self, hist, since):
        [c.send_history(hist, since) for c in self.clients]

    def broadcast_event(self, val):
        [c.send_event(val) for c in self.clients]


class Client:

    def __init__(self, ws, master):
        self.ws = ws
        self.master = master

    def send(self, jsn):
        self.ws.send_str(json.dumps(jsn))

    def send_history(self, hist, since):
        self.send({"h": hist, "since": since})

    def send_event(self, val):
        self.send({"v": val})

    async def run(self):
        js = json.loads(await self.ws.receive_str())
        if csrf_token != js["csrf"]:
            # EVIL
            print("Invalid CSRF token detected!")
            return

        self.send_history(self.master.history, self.master.since)

        async for msg in self.ws:
            if msg.tp == web.MsgType.text:
                js = json.loads(msg.data)
                if js["command"] == "clear":
                    self.master.clear()
            elif msg.tp == web.MsgType.close:
                break

master = Master(spectrometer, logfile = args.log)

async def handle_metadata(req):
    return web.Response(body = metadata_json, content_type = "application/json")

async def handle_data(req):
    ret = "-_-\n---\n"
    for x in master.history:
        ret += ("%d\n" % x)
    return web.Response(body = ret.encode(), content_type = "text/plain")

async def handle_index(req):
    return web.HTTPFound("/index.html")

async def handle_ws(req):
    ws = web.WebSocketResponse()
    await ws.prepare(req)

    cl = Client(ws, master)
    master.clients.append(cl)

    try:
        await cl.run()
    finally:
        master.clients.remove(cl)
    return ws

if __name__ == "__main__":
    app = web.Application()
    app.router.add_route("GET", "/metadata.json", handle_metadata)
    app.router.add_route("GET", "/data.txt", handle_data)
    app.router.add_route("GET", "/", handle_index)
    app.router.add_route("GET", "/ws", handle_ws)
    app.router.add_static("/", "../web")

    asyncio.ensure_future(master.spectrometer_loop())
    web.run_app(app, port = 4000)
