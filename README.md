# Alpha Spectrometer

Alpha spectrometer developed during my internship at the [IEAP](http://www.utef.cvut.cz/ieap).

![img_20160623_162254](https://cloud.githubusercontent.com/assets/3966931/16306822/4c2704d0-395f-11e6-805f-e5962f83f635.jpg)

Pu-239 Am-241 Cm-244 spectrum (on bare die BPW34 in vacuum)

![1213](https://cloud.githubusercontent.com/assets/3966931/16306915/a5d83b2a-395f-11e6-9b39-3084f1c60455.png)

## Protocol

### General structure

```
|----------|---------
|   type   | content...
|----------|---------
```

If the device receives a packet with invalid type, it responds with an ERROR
packet with EUNKNOWN error type.

### Host->Device

#### NOP

This does not do anything, it is recommended to send a bunch of NOPs on opening
the serial port to flush any data which might have been left in the device input
buffer.
```
|----------|
|   0x01   |
|----------|
```
#### PING

Used by host to check whether the device is alive. Device should respond with PONG.
```
|----------|
|   0x02   |
|----------|
```
#### GET

Used by host to get basic properties. Device should respond with GETRESP.
```
|----------|---------|
|   0x03   | propid  |
|----------|---------|
```
#### SET

Used by host to set basic properties. Propval length depends on the property being
set. Note that multi byte values should be sent in little endian.
```
|----------|---------|----------
|   0x04   | propid  | propval...
|----------|---------|----------
```
#### START

Start sampling and sending events.
```
|----------|
|   0x05   |
|----------|
```
#### END

End sampling and sending events.
```
|----------|
|   0x06   |
|----------|
```
### Device->Host

The most significant bit of the type field is always set to 1.

#### PONG

Sent as response to host PING.
```
|----------|
|   0x82   |
|----------|
```
#### EVENT

Send event (little endian).
```
|----------|----------|----------|
|   0x87   |   low    |   high   |
|----------|----------|----------|
```
#### GETRESP
```
|----------|----------|----------
|   0x83   |  propid  |  value...
|----------|----------|----------
```
The value length depends on the propid and the byte order is little endian.

#### WAVE

Sends event waveform. This is currently not yet implemented.
```
|----------|----------|----------
|   0x88   |  length  |  <length> samples, 2 bytes each, Big endian
|----------|----------|----------
```
#### ERROR
```
|----------|----------|
|   0xff   |  errno   |
|----------|----------|
```
Sent on errors.
errno:
  =  1  EUNKNOWN
    -- Sent on unknown packet type received
  =  2  EINKEY
    -- Sent on invalid key in GET/SET packet
  =  3  EINOP
    -- Sent on invalid operation on an existing key (unsuported read/write)

### Properties

#### PROP_FW (0x01)
length = 2

Firmware version version.

#### PROP_THRESH (0x02)
length = 2

Event trigger threshold.

#### PROP_BIAS (0x03)
length = 1

Set to 1 if the internal bias generator should be enabled.

#### PROP_AMP (0x04)
length = 1

Set to 1 if the internal x6 amplifier should be enabled.

#### PROP_RTHRESH (0x05)
length = 2

If the value is > 0, the events are further filtered based on whether their falling edge
is at least N samples longer than the rising edge.

#### PROP_SERNO (0x06)
length = 2

Serial number of the device. Set at compile time using `make SERNO=X`

