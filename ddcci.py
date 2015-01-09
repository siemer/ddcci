#!/usr/bin/python3
# coding: utf-8
from __future__ import print_function

import fcntl, os, binascii, functools, operator, time

# read: 1, write: 0
# first i2c byte is always written, rest is read/write according to rw bit
# write until we are out of bytes or slave nacks (bad; last byte lost?)
# read until we don’t want any more and nack/stop

# length byte first bit: should be 0 on vendor specific msgs
# op codes: 
# 0x01 VCP request
# 0x02 VCP reply
# 0x03 VCP set
# 0x06 timing reply
# 0x07 timing request
# 0x09 VCP reset  (in spec, but what is it?)
# 0x0c save current settings
# 0xa1 display self-test reply
# 0xb1 display self-test request
# 0xc0-0xc8 is vendor specific???
# 0xe1 idetification reply
# 0xe2 table read request
# 0xe3 capabilities reply
# 0xe4 table read reply
# 0xe7 table write
# 0xf1 identification request (to find an internal diplay dependent device)
# 0xf3 capabilities request
# 0xf5 enable application report


# host should
# 1. get ID string
# 2. get capability string
# 3. enable application message report
# ...then ready to go

# Virtual Control Panel (VCP) codes
#
# 0x00-0xdf is MCCS standard
# 0xe0-0xff are manufacturer use
# 0x10 brightness
# 0x12 contrast
# 0x14 select color preset


# Controls
#
# C – Continuous (0-max)
# NC – Non Continuous
# T – Table


examples = {name: bytearray.fromhex(string) for name, string in {
    'enable application report': '6e 51 82 f5 01 49',
    'application test': '6e 51 81 b1 0f',
    'application test reply': '6f 6e 82 a1 00 1d',
    'null message': '6f 6e 80 be',
    # completely nuts, but as in spec
    # excluding first byte (“destination address”), msg is the same
    # source (second byte) is even/odd on writing/reading
    'external: host to touch screen': 'f0 f1 81 b1 31',
    'external: touch screen to host': 'f1 f0 82 a1 00 83',
    'internal: host to touch screen': '6e f1 81 b1 af',
    'internal: touch screen to host': '6f f0 82 a1 00 83',
}.items()}

# dst addr, “src addr”, ((amount of following bytes)-1) & 0x80 if 
#  MCCS std op code to follow, op code, ..., chksum

# (length) from op code, without checksum (wait period afterwards):
# (2) 0x01 get vcp, vcp code (40ms)
# (8) 0x02 get vcp reply, result code: 0x00 no erro or 0x01 unsupported vcp,
#  vcp code, vcp type code: 0x00 set parameter or 0x01 momentary, max value
#  big endian, present value big endian (2 bytes each)
# (4) 0x03 set vcp, vcp code, value big endian (50ms)
# (1) 0x07 get timing report (40ms)
# (7??) no length?? 0x06 get timing report reply, 0x4e “timing messgae op code”,
#  status, horizontal freq big endian, vertical freq big endian
# (1) 0x0c save current settings (200ms)
# (1) 0xb1 application test
# (2) 0xa1 application test reply, status
# (3) 0xf3, offset big endian
# () 0xe3, offset big endian, data [spec: max 32 bytes data] (50ms from reply??)


messages = {
  'request current brightness': '6e 51 82 01 10',
  # at least 40ms later
  'read current brightness': '6f 6e 88 02 00 10',
  'set brightness': '6e 51 84 03 10 00 32', # and wait 50ms
  'save current settings': '6e 51 81 0c', # wait 200ms before next msg
  'request capabilities': '6e 51 83 f3 00 00',
  'read capabilities': '6f 6e a3 e3 00 00 ', # wait 50ms now or in between?
  'request timing report': '6e 51 81 07', # wait 40ms
  'red timing report': '6f 6e 06 4e 00 00 00 00 00', # wait 50ms before next
  'write table': '6e 51 a3 e7 73 00 00 ', # wait 50ms
  'request table': '6e 51 83 e2 73 00 00', # 83 or better 84?
  'read table': '6f 6e a3 e4 00 00 ', # wait 50ms
}

def i2c_to_ddcci(i2c):
  # in case of reading from device, for checksum calculation
  # assume 0x50 as first byte (address + r/w (here: writing!?))
  if i2c[0] & 1:  # if i2c[0] == 0x6f and i2c[1] == 0x6e:
    i2c[0] = 0x50
  return i2c

def i2c_to_dev(pseudo_i2c):
  """converts bytes as they would be written over i2c to i2c-dev compatible
     write() strings. Aehm... sorry, not absolutely right: the checksum
     is also added."""

  i2c_to_ddcci(pseudo_i2c)
  pseudo_i2c.append(checksum(pseudo_i2c))


def checksum(seq):
  return functools.reduce(operator.xor, seq)

class DDCCI(object):
  I2C_SLAVE = 0x0703
  ADDR = 0x37
  WAIT = 0.05  # 50ms
  _send = bytes.fromhex('6e 51')
  _receive = bytes.fromhex('6f 6e')

  def __init__(self, channel):
    self._dev = os.open('/dev/i2c-' + str(channel), os.O_RDWR)
    fcntl.ioctl(self._dev, DDCCI.I2C_SLAVE, DDCCI.ADDR)

  def write(opcode, vcpcode=None, value=None):
    time.sleep(DDCCI.WAIT)
    ba = bytearray() + DDCCI._send
    ba.append(opcode)
    if vcpcode:
      ba.append(vcpcode)
      if value:
        ba.append(value)
    ba.append(checksum(ba))
    os.write(self.dev, ba)

  def read(opcode, vcpcode=None):
    time.sleep(DDCCI.WAIT)
    b = os.read(self.dev, 100)
    print(b)
    assert b[0] == DDCCI._receive[1]
    bb = i2c_to_ddcci(bytearray(DDCCI._receive[0] + b))
    print('checksum', checksum(bb))

def check_examples():
  for key in examples:
    ex = i2c_to_ddcci(examples[key])
    if checksum(ex) != 0:
      print('checksum error for message:', key)

if __name__ == '__main__':
  check_examples()
  d = DDCCI(1)
