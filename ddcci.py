#!/usr/bin/python3
# coding: utf-8
from __future__ import print_function

import fcntl, os, binascii

I2C_SLAVE = 0x0703

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
    'wrong checksum test message': '1234 abcd',
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
  'ask for current brightness setting': '6e 51 82 01 10',
  # at least 40ms later
  'read reply': '6f 6e

def example_i2c_to_ddcci(i2c):
  # in case of reading from device, for checksum calculation
  # assume 0x50 as first byte (address + r/w (here: writing!?))
  if i2c[0] & 1:  # if i2c[0] == 0x6f and i2c[1] == 0x6e:
    i2c[0] = 0x50
  return i2c

if __name__ == '__main__':
  dev = os.open('/dev/i2c-6', os.O_RDWR)
  # fcntl.ioctl(dev, I2C_SLAVE, 0x50)
  for key in examples:
    ex = example_i2c_to_ddcci(examples[key])
    checksum = 0
    for byte in ex:
      checksum ^= byte
    if checksum != 0:
      print('checksum error for message:', key)

  # print(os.read(dev, 1))
