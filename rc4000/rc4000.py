#!/usr/bin/python
# -*- coding: UTF-8 -*-

# Requires pyserial. Install via:
# pip install pyserial

from __future__ import print_function

import logging
import struct
from enum import Enum

from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
port = "/dev/cu.usbserial-401210"
baudrate = 115200

# Prepare serial connection.
ser = Serial(port, baudrate=baudrate, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE, timeout=1)


# ser.flushInput()

# ser.write(b"GT+INFO")
def SendGTCmd(cmd: bytes):
    log.debug("sending '%s'", cmd)
    ser.write(cmd)


def gt_info():
    gt_sendcmd(b'GT+INFO')


def gt_sendcmd(cmd: bytes):
    log.debug("sending '%s'", cmd)
    ser.write(cmd + b"\r\n")


def gt_getmd():
    gt_sendcmd(b'GT+GETMD')


def gt_getpwd():
    gt_sendcmd(b'GT+GETPWD')


def cmd_callback(line: bytes):
    print("line=%s" % line)
    if line == "GT: READY":
        SendGTCmd(b"GT+INFO\r\n")  # GT+GETMD\r\nGT+GETPWD")
    elif line == b'+GETDEV: "RC-4000"':
        log.debug("found rc-4000")
    elif line.startswith(b'+REB: '):
        log.debug("rebooting")
    elif line.startswith(b'+GTINCALL: '):
        phone = line.replace(b'+GTINCALL: ', b'')
        log.debug("in call from %s", phone)
    elif line.startswith(b'+GT: CALL DIS'):
        log.debug("in call ended")
    elif line == b'+GTLOAD: 1':
        log.debug("relay ON")
    elif line == b'+GTLOAD: 0':
        log.debug("relay OFF")
    elif line.startswith(b'+GTWRPN: '):
        phone = line.replace(b'+GTINCALL: ', b'')
        log.debug("new number: %s", phone)
        gt_info()
    elif line.startswith(b'+GETMD: '):
        mode = line.replace(b'+GETMD: ', b'')
        log.debug("mode is %s", mode)

        class RCMode(Enum):
            NORMAL: int = 0
            ACCESS: int = 1
            DOOR: int = 2
            UNKNOWN: int = 3

        try:
            log.debug(RCMode(value=int(mode)))
        except ValueError:
            log.debug("mode is UNKNOWN")

    elif line.startswith(b'+AUTH: '):
        result = line.replace(b'+AUTH: ', b'')
        if result == b'1':
            log.debug('auth ok')
            gt_info()
            gt_getmd()
            # gt_getpwd()
        else:
            log.debug('auth error')
    elif line.startswith(b'+GTSMS: '):
        sms = line.replace(b'+GTINCALL: ', b'')
        log.debug("in sms: %s", sms)
    else:
        log.error("unknown %s", line)


# SendGTCmd(b"GT+INFO\r\nGT+GETMD\r\nGT+GETPWD\r\n")
# SendGTCmd(b"GT+GETDEV\r\n")
SendGTCmd(b"GT+AUTH=8052\r\n")
line: bytes = b""
while True:
    b = ser.read(size=1)
    # print("b=%s" % b)
    if not b:
        # empty read
        continue

    if b == b'\r':
        line = line.strip()  # remove "\n"?
        cmd_callback(line)
        line = b""
    else:
        line = line + b

HEADER_BYTE = b"\xAA"
COMMANDER_BYTE = b"\xC0"
TAIL_BYTE = b"\xAB"

byte, previousbyte = b"\x00", b"\x00"

while True:
    previousbyte = byte
    byte = ser.read(size=1)
    # print(byte)

    # We got a valid packet header.
    if previousbyte == HEADER_BYTE and byte == COMMANDER_BYTE:
        packet = ser.read(size=8)  # Read 8 more bytes
        # print(packet)

        # Decode the packet - little endian, 2 shorts for pm2.5 and pm10, 2 ID bytes, checksum.
        readings = struct.unpack('<HHcccc', packet)

        # Measurements.
        pm_25 = readings[0] / 10.0
        pm_10 = readings[1] / 10.0

        # ID
        did = packet[4:6]
        # print(id)

        # Prepare checksums.
        checksum = readings[4][0]
        calculated_checksum = sum(packet[:6]) & 0xFF
        checksum_verified = (calculated_checksum == checksum)
        # print(checksum_verified)

        # Message tail.
        tail = readings[5]

        if tail == TAIL_BYTE and checksum_verified:
            # print("PM 2.5:", pm_25, "μg/m^3  PM 10:", pm_10, "μg/m^3")
            # print("PM 2.5:", pm_25, "µg/m³  PM 10:", pm_10, "µg/m³  ID:", bytes(id).hex())
            # print("PM 2.5:%s µg/m³  PM 10:%s µg/m³ ID:%s" % (pm_25, pm_10, bytes(did)) )
            print("pm25=%s; pm10=%s" % (pm_25, pm_10))
