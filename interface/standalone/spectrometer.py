# The MIT License (MIT)
#
# Copyright (C) 2015-1016 Institute of Applied and Experimental Physics (http://www.utef.cvut.cz/)
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

import datetime
import functools
import operator
import random
import serial
import struct
import time

class Spectrometer:

    def __init__(self, channels):
        self.channels = channels

    def start(self):
        pass

    def end(self):
        pass

    def __iter__(self):
        return self

    def next_event(self):
        raise NotImplementedError

    def __next__(self):
        return self.next_event()

    def flush(self):
        pass

class DummySpectrometer(Spectrometer):

    def __init__(self, period = 1, chans = 1024):
        super(DummySpectrometer, self).__init__(channels = chans)
        self.period = period
        self._last = time.time()
        self.chans = chans
        self.fw_version = "1.0"

    def next_event(self):
        dt = time.time() - self._last
        if dt < self.period:
            time.sleep(self.period)
        self._last += self.period
        return int(random.gauss(200, 10)) if random.random() < 0.1 else int(random.gauss(2000, 300))

    def flush(self):
        self._last = time.time()

class SIPOSSpectrometer(Spectrometer):

    def __init__(self, sername):
        super(SIPOSSpectrometer, self).__init__(channels = 4096)
        self._ser = serial.Serial(sername, 500000)
        self.fw_version = "0.0"

    def next_event(self):
        at = self._ser.read(2)
        return (((at[0] & 0x3f) << 6) | (at[1] & 0x7f)) ^ 0xfff

    __next__ = next_event


class SerSpectException(Exception):

    def __init__(self, errorcode):
        self.errorcode = errorcode

class SerSpect(Spectrometer):

    # Host->Device
    PACK_NOP = 0x01
    PACK_PING = 0x02
    PACK_GET = 0x03
    PACK_SET = 0x04
    PACK_START = 0x05
    PACK_END = 0x06

    # Device->Host
    PACK_PONG = 0x82
    PACK_GETRESP = 0x83
    PACK_EVENT = 0x87
    PACK_WAVE = 0x88
    PACK_ERROR = 0xff

    PROP_FW = 0x01
    PROP_THRESH = 0x02
    PROP_BIAS = 0x03
    PROP_AMP = 0x04

    PACK_LENGTH_MAP = {
        PACK_PONG: 1,
        PACK_GETRESP: None, # See PROP_LENGTH_MAP
        PACK_EVENT: 3,
        PACK_ERROR: 2,
    }

    PROP_LENGTH_MAP = {
        PROP_FW: 2,
        PROP_THRESH: 2,
        PROP_BIAS: 1,
        PROP_AMP: 1,
    }

    def __init__(self, sername):
        super(SerSpect, self).__init__(channels = 4096)
        self._packqueue = []
        self._ser = serial.Serial(sername, 115200)
        self._ser.write([SerSpect.PACK_NOP] * 100)
        self.end()
        self.set_prop(SerSpect.PROP_BIAS, 0)
        self.set_prop(SerSpect.PROP_AMP, 0)
        self.flush()

        ver = self.get_prop(SerSpect.PROP_FW)
        self.fw_version = "%d.%d" % (ver >> 8, ver & 0xff)

    @staticmethod
    def _encode_lendian(val, ln):
        return functools.reduce(operator.add, [bytes([(val >> (i * 8)) & 0xff]) for i in range(ln)])

    @staticmethod
    def _decode_lendian(bytss):
        return functools.reduce(operator.add,
                                map(lambda i, v: v << (i * 8), *zip(*enumerate(bytss))))

    @property
    def timeout(self):
        return self._ser._timeout

    @timeout.setter
    def timeout(self, v):
        self._ser.timeout = v

    def ping(self):
        self.send_packet(SerSpect.PACK_PING)
        self.recv_packet_queued(SerSpect.PACK_PONG)

    def start(self):
        self.send_packet(SerSpect.PACK_START)

    def end(self):
        self.send_packet(SerSpect.PACK_END)

    def set_prop(self, prop, val):
        self.send_packet(SerSpect.PACK_SET,
                         prop,
                         SerSpect._encode_lendian(val,
                                                  SerSpect.PROP_LENGTH_MAP[prop]))

    def get_prop(self, prop):
        self.send_packet(SerSpect.PACK_GET, prop)
        return SerSpect._decode_lendian(
                    self.recv_packet_queued(SerSpect.PACK_GETRESP)[2:])

    def recv_packet_queued(self, typ):
        for p in self._packqueue:
            if p[0] == typ:
                self._packqueue.remove(p)
                return p
        while True:
            p = self.recv_packet()
            if p[0] == typ:
                return p
            self._packqueue.append(p)

    def send_packet(self, *args):
        self._ser.write(
            functools.reduce(
                    operator.add,
                    map(bytes, [[x] if isinstance(x, int) else x for x in args])))

    def recv_packet(self):
        while True:
            pack = self._ser.read(1)
            typ = pack[0]
            if typ == SerSpect.PACK_GETRESP:
                pack += self._ser.read(1)
                propid = pack[-1]
                return pack + self._ser.read(SerSpect.PROP_LENGTH_MAP[propid])
            elif typ == SerSpect.PACK_WAVE:
                pack += self._ser.read(1)
                return pack + self._ser.read(pack[-1] * 2)
            elif typ in SerSpect.PACK_LENGTH_MAP:
                ln = SerSpect.PACK_LENGTH_MAP[typ]
                return pack + (self._ser.read(ln - 1) if ln > 1 else b"")
            # Drop the byte

    def next_event(self):
        p = self.recv_packet_queued(SerSpect.PACK_EVENT)
        return self._decode_lendian(p[1:])

    def next_wave(self):
        p = self.recv_packet_queued(SerSpect.PACK_WAVE)
        return struct.unpack(">%dH" % p[1], p[2:])

    def flush(self):
        self._packqueue.clear()
        self._ser.flush()

    def close(self):
        self._ser.close()


class HistFile:

    def __init__(self):
        self.vals = []

    @staticmethod
    def load_file(fname):
        ret = HistFile()
        with open(fname) as f:
            line = f.readline()
            if line != "-_-\n":
                raise ValueError("Invalid magic line %s" % start)
            while line != "---\n":
                spl = line.split(": ", maxsplit = 1)
                if len(spl) == 2:
                    key, val = (s.strip() for s in spl)
                    key = key.lower()
                    if key in ["from", "to"]:
                        val = datetime.datetime.fromtimestamp(int(val))
                        if key == "from":
                            key = "from_"
                    setattr(ret, key, val)
                line = f.readline()
            for l in f:
                ret.vals.append(int(l))
        return ret
