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

import asyncio
import atexit
import collections
import datetime
import functools
import operator
import random
import re
import serial
import serial.aio
import struct
import subprocess
import sys
import time
from serial.tools import list_ports


class ConfigProp:

    def __init__(self, spect, id, name, fr, to):
        self.id = id
        self.name = name
        self.fr = fr
        self.to = to


class Spectrometer:

    def __init__(self, channels):
        self.channels = channels
        self.configprops = []
        self.fw_version = "NONE"

    def start(self):
        pass

    def end(self):
        pass

    async def next_event(self):
        raise NotImplementedError

    def set_prop(self, prop, val):
        raise NotImplementedError

    async def get_prop(self, prop):
        raise NotImplementedError

    async def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.next_event()


class DummySpect(Spectrometer):

    Event = collections.namedtuple("Event", ["value"])

    def __init__(self, period=1, channels=1024):
        super(DummySpect, self).__init__(channels=channels)
        self.period = period
        self._last = time.time()
        self.fw_version = "1.0"

    async def next_event(self):
        dt = time.time() - self._last
        if dt < self.period:
            await asyncio.sleep(self.period - dt)
        self._last += self.period
        val = None
        while val is None or val <= 0 or val > self.channels:
            val = random.gauss(0.05, 0.025) if random.random() < 0.2 else random.gauss(0.5, 0.075)
            val *= self.channels
            val = int(val)
        return DummySpect.Event(value=val)


class AsyncSerialSpectrometer(Spectrometer, asyncio.Protocol):

    _description = None

    def __init__(self, channels):
        super(AsyncSerialSpectrometer, self).__init__(channels=channels)
        self._initsem = asyncio.Semaphore(value=0)
        self._recvqueue = asyncio.Queue()

    def connection_made(self, transport):
        self._transport = transport
        self._initsem.release()

    def data_received(self, data):
        for x in range(len(data)):
            self._recvqueue.put_nowait(data[x:x + 1])

    async def recv(self, nbytes=1):
        ret = b""
        for _ in range(nbytes):
            ret += await self._recvqueue.get()
        return ret

    @classmethod
    async def connect(cls, port=None):
        if port is None and cls._description is not None:
            for s in list_ports.comports():
                if re.match(cls._description, s.description):
                    port = s.device
        transport, spect = await serial.aio.create_serial_connection(
                                asyncio.get_event_loop(), cls, port, cls._initbaud)
        await spect._initsem.acquire()
        await spect._ainit()
        return spect

    async def _ainit(self):
        pass

    def flush(self):
        self._recvqueue = asyncio.Queue()

    def close(self):
        self._transport.close()


class SIPOSSpect(AsyncSerialSpectrometer):

    Event = collections.namedtuple("Event", ["value"])

    _description = "Photodiode Spectrometer"
    _initbaud = 500000

    def __init__(self, sername):
        super(SIPOSSpect, self).__init__(channels=4096)

    async def next_event(self):
        at = await self.recv(2)
        val = (((at[0] & 0x3f) << 6) | (at[1] & 0x7f)) ^ 0xfff
        return SIPOSSpect.Event(value=val)


class SerSpectException(Exception):

    def __init__(self, errorcode):
        self.errorcode = errorcode


class SerSpect(AsyncSerialSpectrometer):

    Event = collections.namedtuple("Event", ["value"])

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
    PROP_RTHRESH = 0x05
    PROP_SERNO = 0x06

    PACK_LENGTH_MAP = {
        PACK_PONG: 1,
        PACK_GETRESP: None,  # See PROP_LENGTH_MAP
        PACK_EVENT: 3,
        PACK_ERROR: 2,
    }

    PROP_LENGTH_MAP = {
        PROP_FW: 2,
        PROP_THRESH: 2,
        PROP_BIAS: 1,
        PROP_AMP: 1,
        PROP_RTHRESH: 2,
        PROP_SERNO: 2,
    }

    _description = "Spectrometer Acquisition Board"
    _initbaud = 115200  # Does not matter really

    def __init__(self):
        super(SerSpect, self).__init__(channels=4096)
        self.event_loop = asyncio.get_event_loop()
        self._packqueues = [asyncio.Queue() for _ in range(256)]
        self._packlock = asyncio.Lock()
        self._proplock = asyncio.Lock()

        self._transport = None

        self.configprops = [
            ConfigProp(self, self.PROP_THRESH, "Threshold", 0, 4096),
            ConfigProp(self, self.PROP_RTHRESH, "Ratio Thresh", 0, 100),
            ConfigProp(self, self.PROP_BIAS, "Bias", 0, 1),
            ConfigProp(self, self.PROP_AMP, "Amp", 0, 1),
        ]

    async def _ainit(self):
        # Flush the device buffer if it has not been flushed yet
        self._transport.write([SerSpect.PACK_NOP] * 100)
        self.flush()
        asyncio.ensure_future(self._recv_loop())
        self.set_prop(SerSpect.PROP_BIAS, 0)
        self.set_prop(SerSpect.PROP_AMP, 0)

        ver = await self.get_prop(SerSpect.PROP_FW)
        self.fw_version = "%d.%d" % (ver >> 8, ver & 0xff)

        self.serno = await self.get_prop(SerSpect.PROP_SERNO)

    async def _recv_loop(self):
        while True:
            pack = await self.recv_packet()
            self._packqueues[pack[0]].put_nowait(pack)

    @staticmethod
    def _encode_lendian(val, ln):
        return functools.reduce(operator.add, [bytes([(val >> (i * 8)) & 0xff]) for i in range(ln)])

    @staticmethod
    def _decode_lendian(bytss):
        return functools.reduce(operator.add,
                                map(lambda i, v: v << (i * 8), *zip(*enumerate(bytss))))

    async def ping(self):
        self.send_packet(SerSpect.PACK_PING)
        await self.recv_packet_queued(SerSpect.PACK_PONG)

    def start(self):
        self.send_packet(SerSpect.PACK_START)

    def end(self):
        self.send_packet(SerSpect.PACK_END)

    def set_prop(self, prop, val):
        self.send_packet(SerSpect.PACK_SET,
                         prop,
                         SerSpect._encode_lendian(val,
                                                  SerSpect.PROP_LENGTH_MAP[prop]))

    async def get_prop(self, prop):
        async with self._proplock:
            self.send_packet(SerSpect.PACK_GET, prop)
            pack = await self.recv_packet_queued(SerSpect.PACK_GETRESP)
            return SerSpect._decode_lendian(pack[2:])

    async def recv_packet_queued(self, typ):
        return await self._packqueues[typ].get()

    def send_packet(self, *args):
        self._transport.write(
            functools.reduce(
                    operator.add,
                    map(bytes, [[x] if isinstance(x, int) else x for x in args])))

    async def recv_packet(self):
        async with self._packlock:
            while True:
                pack = await self.recv(1)
                typ = pack[0]
                if typ == SerSpect.PACK_GETRESP:
                    pack += await self.recv(1)
                    propid = pack[-1]
                    return pack + (await self.recv(SerSpect.PROP_LENGTH_MAP[propid]))
                elif typ == SerSpect.PACK_WAVE:
                    pack += await self.recv(1)
                    return pack + (await self.recv(pack[-1] * 2))
                elif typ in SerSpect.PACK_LENGTH_MAP:
                    ln = SerSpect.PACK_LENGTH_MAP[typ]
                    return pack + ((await self.recv(ln - 1)) if ln > 1 else b"")
                # Drop the byte

    async def next_event(self):
        p = await self.recv_packet_queued(SerSpect.PACK_EVENT)
        val = self._decode_lendian(p[1:])
        return SerSpect.Event(value=val)

    async def next_wave(self):
        p = await self.recv_packet_queued(SerSpect.PACK_WAVE)
        return struct.unpack(">%dH" % p[1], p[2:])


class DM100(Spectrometer):

    Event = collections.namedtuple("Event", ["header0", "header1", "packet_id",
                                             "value", "waveform", "tot",
                                             "timestamp", "checksum_valid"])

    class SingleByteRegister:

        def __init__(self, cmd):
            self.cmd = cmd
            self.val = 0

        def __get__(self, obj, obtype=None):
            if obj is None:
                return self
            return self.val

        def __set__(self, obj, val):
            self.val = val
            obj.send_command(self.cmd, val)

    class DualByteRegister:

        def __init__(self, cmdhi, cmdlo=None):
            self.cmdhi = cmdhi
            self.cmdlo = cmdhi + 1 if cmdlo is None else cmdlo
            self.val = 0

        def __get__(self, obj, obtype=None):
            if obj is None:
                return self
            return self.val

        def __set__(self, obj, val):
            obj.send_command(self.cmdhi, (val >> 8) & 0xff)
            obj.send_command(self.cmdlo, val & 0xff)

    class RegBit:

        def __init__(self, reg, off):
            self.reg = reg
            self.off = off

        def __get__(self, obj, obtype=None):
            if obj is None:
                return self
            return bool(self.reg.__get__(obj) & (1 << self.off))

        def __set__(self, obj, val):
            rval = self.reg.__get__(obj)
            rval &= ~(1 << self.off)
            rval |= int(bool(val)) << self.off
            self.reg.__set__(obj, rval)

    class RegVal:

        def __init__(self, reg, off, width):
            self.reg = reg
            self.off = off
            self.mask = ((1 << width) - 1) << self.off

        def __get__(self, obj, obtype=None):
            if obj is None:
                return self
            return (self.reg.__get__(obj) & self.mask) >> self.off

        def __set__(self, obj, val):
            rval = self.reg.__get__(obj)
            rval &= ~self.mask
            rval |= (val << self.off) & self.mask
            self.reg.__set__(obj, rval)

    # https://support.dce.felk.cvut.cz/mediawiki/images/b/ba/Bp_2016_kalousek_jiri.pdf

    CMD_LLD_HIGH = 128
    CMD_LLD_LOW = 129
    CMD_ULD_HIGH = 130
    CMD_ULD_LOW = 131
    CMD_HYSTERESIS = 132
    CMD_CLKMUX = 133
    CMD_PRETRIG_HIGH = 134
    CMD_PRETRIG_LOW = 135
    CMD_COUNT_HIGH = 136
    CMD_COUNT_LOW = 137
    CMD_POSTTRIG_HIGH = 138
    CMD_POSTTRIG_LOW = 139
    CMD_MODE = 140
    CMD_TRIGCFG = 142
    CMD_PACKCFG = 143
    CMD_MASKDATA = 148
    CMD_DISABLE_INHIBIT = 144
    CMD_TRIGGER = 141
    CMD_ENABLE_INHIBIT = 191

    MODE_SAMPLE = 0b000
    MODE_SAMPLE_TOT = 0b001
    MODE_WAVEFORM = 0b100

    START_MODE_LLD = 0b00
    START_MODE_EXT = 0b01

    END_MODE_LLD = 0b00
    END_MODE_COUNT = 0b01

    lld = DualByteRegister(CMD_LLD_HIGH, CMD_LLD_LOW)
    uld = DualByteRegister(CMD_ULD_HIGH, CMD_ULD_HIGH)
    hystheresis = SingleByteRegister(CMD_HYSTERESIS)
    clkmux = SingleByteRegister(CMD_CLKMUX)
    pretrig = DualByteRegister(CMD_PRETRIG_HIGH, CMD_PRETRIG_LOW)
    count = DualByteRegister(CMD_COUNT_HIGH, CMD_COUNT_LOW)
    posttrig = DualByteRegister(CMD_POSTTRIG_HIGH, CMD_POSTTRIG_LOW)
    modecfg = SingleByteRegister(CMD_MODE)
    trigcfg = SingleByteRegister(CMD_TRIGCFG)
    packcfg = SingleByteRegister(CMD_PACKCFG)
    maskcfg = SingleByteRegister(CMD_MASKDATA)

    mode = RegVal(modecfg, 4, 3)
    start_mode = RegVal(modecfg, 2, 2)
    end_mode = RegVal(modecfg, 0, 2)

    gothrough = RegBit(trigcfg, 7)
    derandom = RegBit(trigcfg, 6)
    dealter = RegBit(trigcfg, 5)
    polarity = RegBit(trigcfg, 4)
    extrigcfg = RegVal(trigcfg, 2, 2)
    gatecfg = RegVal(trigcfg, 0, 2)

    addheader = RegBit(packcfg, 7)
    addtime = RegBit(packcfg, 6)
    addchecksum = RegBit(packcfg, 5)
    bus8 = RegBit(packcfg, 0)

    addlost = RegBit(maskcfg, 7)

    def __init__(self, proc):
        super(DM100, self).__init__(channels=65536)
        self._proc = proc
        self.pipe = self._proc.stdin
        self._queue = asyncio.Queue()

    @staticmethod
    async def connect():
        proc = await asyncio.create_subprocess_exec(
                            "ieapspect-wrapper-dm100",
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=sys.stderr)

        def _kill_on_exit():
            proc.kill()
        atexit.register(_kill_on_exit)

        ret = DM100(proc)
        await ret._ainit()
        return ret

    async def _ainit(self):
        m1 = await self.read_masked(1)
        self.fw_version = "%d.%d" % ((m1[0] >> 3) & 0x1f, m1[0] & 0x07)
        self.msps = m1[1]
        m2 = await self.read_masked(2)
        self.resolution = (m2[1] & 0x0f) + 1
        self.optype = "LTC" if (m2[0] & 0x80) else "ADA"
        self.divide = 5 if (m2[0] & 0x40) else 1
        self.termination = 50 if (m2[0] & 0x20) else 1000
        self.extref = not bool(m2[0] & 0x10)
        self.irefrng = 1.0 if bool(m2[0] & 0x08) else 0.5
        self.dccoupled = bool(m2[0] & 0x04)
        await asyncio.sleep(0.1)
        if self._proc.returncode is not None:
            from subprocess import CalledProcessError
            raise CalledProcessError("Failed to start the DM100 wrapper")

        self.modecfg = 0x04
        self.lld = 0x0000
        self.uld = 0x0000
        self.hystheresis = 0x00
        self.clkmux = 0x00
        self.pretrig = 0x0000
        self.count = 0x0000
        self.posttrig = 0x0000
        self.trigcfg = 0x00
        self.packcfg = 0x00
        self.maskcfg = 0x00
        self.modecfg = 0x00
        self.bus8 = True
        self.addheader = False
        self.addtime = True
        self.addchecksum = False
        self.polarity = True
        self.mode = DM100.MODE_SAMPLE

    def start(self):
        self.disable_inhibit()

    def send_command(self, cmd, data=0):
        bs = bytes([cmd, data])
        self._proc.stdin.write(bs)

    async def read_masked(self, msk):
        self.set_mask(msk)
        self.disable_inhibit()
        self.sw_trigger()
        self.enable_inhibit()
        return (await self._recv(4))

    def set_mask(self, mask):
        self.send_command(DM100.CMD_MASKDATA, mask)

    def enable_inhibit(self):
        self.send_command(DM100.CMD_ENABLE_INHIBIT)

    def disable_inhibit(self):
        self.send_command(DM100.CMD_DISABLE_INHIBIT)

    def sw_trigger(self):
        self.send_command(DM100.CMD_TRIGGER)

    async def next_event(self):
        # Calculate the packet length based on the device settings
        data = []
        header0 = None
        header1 = None
        packet_id = None
        if self.addheader:
            data.extend(await self._recv_words(2))
            header0 = data[0]
            header1 = data[1]
            packet_id = (header1 >> 8) & 0b1111
        dln = await self._recv_word()
        data.append(dln)
        samples = await self._recv_words(dln)
        value = None
        tot = None
        waveform = None
        if self.mode == DM100.MODE_SAMPLE:
            value = samples[0]
        elif self.mode == DM100.MODE_SAMPLE_TOT:
            value = samples[0]
            tot = samples[1]
        elif self.mode == DM100.MODE_WAVEFORM:
            value = max(samples)
            waveform = samples
        data += samples
        times = None
        if self.addtime:
            tws = await self._recv_words(3)
            times = (tws[0] << 32) | (tws[1] << 16) | tws[2]
            data.extend(tws)
        lost = None
        if self.addlost:
            lost = await self._recv_word()
            data.append(lost)
        checksum = None
        if self.addchecksum:
            checksum = await self._recv_word()
            data.append(checksum)

        checksum_valid = None
        if checksum is not None:
            scheck = (sum(data[:-1]) & 0xffff)
            checksum_valid = scheck == checksum

        return DM100.Event(
                    header0=header0,
                    header1=header1,
                    packet_id=packet_id,
                    value=value,
                    tot=tot,
                    waveform=waveform,
                    timestamp=times,
                    checksum_valid=checksum_valid)

    async def _recv_word(self):
        w = await self._recv(2)
        return (w[0] << 8) | w[1]

    async def _recv_words(self, n):
        ret = [0] * n
        bs = await self._recv(n * 2)
        for x in range(n):
            ret[x] = (bs[x * 2] << 8) | bs[x * 2 + 1]
        return ret

    async def _recv(self, n):
        sr = self._proc.stdout
        while len(sr._buffer) < n:
            # Apparently, this is evil and could lead to deadlocks if
            # n > sr._limit (see StreamReader.readexactly sources)
            await sr._wait_for_data("")
        ret = await sr.read(n)
        assert len(ret) == n
        return ret

        ret = await self._proc.stdout.readexactly(n)
        return ret


class Spectrig(Spectrometer, asyncio.SubprocessProtocol):

    Event = collections.namedtuple("Event", ["waveform", "timestamp"])

    class CmdProp:

        def __init__(self, cmd):
            self.cmd = cmd
            self.val = 0

        def __get__(self, obj, obtype=None):
            if obj is None:
                return self
            return self.val

        def __set__(self, obj, val):
            self.val = val
            obj._send_packet(self.cmd, [0x00, (val >> 8) & 0xff, val & 0xff])

    PACKET_HEADER = 0x55

    PACKET_RESP_HEADER = 0xaa
    PACKET_RESP_TAIL = 0xaf

    # Note that according to the magical C# file I have the comparator is not
    # supported

    CMD_TEST = 0x00
    CMD_BIAS = 0x07
    CMD_POWER = 0x41
    #CMD_SET_COMPARATOR = 0x05
    CMD_SET_THRESHOLD = 0x10
    CMD_SET_SAMPLE_COUNT = 0xa1
    CMD_SET_SAMPLE_RATE = 0xa0
    CMD_ENABLE = 0xa2
    CMD_SET_PRETRIG = 0xa3
    CMD_SET_TRIG_SRC = 0xa4
    CMD_SW_TRIGGER = 0xa5
    CMD_COND_OUT = 0xa6
    CMD_SET_SIGNAL_PARAMS = 0xa7
    CMD_CLEAR_SIGNAL_PARAMS = 0xa8

    #TRIGGER_SOURCE_COMPARATOR = 0x00
    TRIGGER_SOURCE_THRESHOLD = 0x01
    TRIGGER_SOURCE_SOFTWARE = 0x02
    TRIGGER_SOURCE_EXTERNAL = 0x03

    PACK_TYPE_CMD = 0xfe
    PACK_TYPE_SPECTRO = 0xff

    threshold = CmdProp(CMD_SET_THRESHOLD)
    sample_count = CmdProp(CMD_SET_SAMPLE_COUNT)
    sample_rate = CmdProp(CMD_SET_SAMPLE_RATE)
    pretrig = CmdProp(CMD_SET_PRETRIG)

    def __init__(self):
        super(Spectrig, self).__init__(channels=4096)
        self.pipe = None
        self.trans = None
        self._buffer = collections.deque()
        self._cmdqueue = asyncio.Queue()
        self._evqueue = asyncio.Queue()

    @staticmethod
    async def connect():
        loop = asyncio.get_event_loop()

        create = loop.subprocess_exec(lambda: Spectrig(),
                                      "ieapspect-wrapper-spectrig")
        trans, prot = await create

        def _kill_on_exit():
            trans.kill()
        atexit.register(_kill_on_exit)

        prot.pipe = trans.get_pipe_transport(0)
        prot.trans = trans
        await prot._ainit()
        return prot

    async def _ainit(self):
        self.disable_measurement()
        self._send_packet(Spectrig.CMD_SET_TRIG_SRC, [0x00, 0x00, Spectrig.TRIGGER_SOURCE_THRESHOLD])
        await asyncio.sleep(0.1)
        # TODO: Add a proper handshake
        if self.trans.get_returncode() is not None:
            from subprocess import CalledProcessError
            raise CalledProcessError("Failed to start the Spectrig wrapper")

    def _send_packet(self, cmd, pars=[0, 0, 0]):
        pack = []
        pack.append(Spectrig.PACKET_HEADER)
        pack.append(cmd)
        pack.extend(pars)
        xor = 0
        for x in pack[1:]:
            xor ^= x
        pack.append(xor)
        self.pipe.write(bytes(pack))

    def start(self):
        self.enable_measurement()

    async def next_event(self):
        return await self._evqueue.get()

    def sw_trigger(self):
        self._send_packet(Spectrig.CMD_SW_TRIGGER)

    def enable_measurement(self):
        self._send_packet(Spectrig.CMD_ENABLE, [0x00, 0x00, 0x01])

    def disable_measurement(self):
        self._send_packet(Spectrig.CMD_ENABLE, [0x00, 0x00, 0x00])

    def _handle_packet_cmd(self, pack):
        pass

    def _handle_packet_spectro(self, pack):
        #packid = pack[1] & 0b00111111
        #trigmark = pack[2] & 0x3f
        #pulsepart = pack[2] & 0xc0
        dlen, = struct.unpack(">H", pack[514:516])
        vals = struct.unpack(">%dH" % dlen, pack[2:2 + dlen * 2])
        ts = 0
        for x in pack[517:517 + 8]:
            ts = (ts << 8) | x

        ev = Spectrig.Event(waveform=vals, timestamp=ts)
        self._evqueue.put_nowait(ev)

    def _handle_packet(self, pack):
        type_ = pack[0]
        if type_ == Spectrig.PACK_TYPE_CMD:
            self._handle_packet_cmd(pack)
        elif type_ == Spectrig.PACK_TYPE_SPECTRO:
            self._handle_packet_spectro(pack)
        else:
            # Probably some bytes got lost, let's hope that we can resync soon
            pass

    def pipe_data_received(self, fd, data):
        for b in data:
            self._buffer.append(b)
        while len(self._buffer) >= 526:
            start = False
            while len(self._buffer) >= 526:
                if self._buffer.popleft() == Spectrig.PACKET_RESP_HEADER:
                    start = True
                    break
            if not start:
                break
            if self._buffer[524] != Spectrig.PACKET_RESP_TAIL:
                # This is not a valid packet
                self._buffer.popleft()
                continue
            pack = bytes([self._buffer.popleft() for _ in range(525)])
            self._handle_packet(pack)

    def process_exited(self):
        pass


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
                spl = line.split(": ", maxsplit=1)
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
