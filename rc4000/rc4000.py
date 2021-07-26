#!/usr/bin/python
# -*- coding: UTF-8 -*-

# Requires pyserial. Install via:
# pip install pyserial

from __future__ import print_function

import logging
from enum import Enum

from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def addressbook():
    return ("+380",)


def gt_auth(pin: int):
    gt_sendcmd(b"GT+AUTH=%s" % pin)


def gt_info():
    gt_sendcmd(b"GT+INFO")


def gt_sendcmd(cmd: bytes):
    log.debug("sending '%s'", cmd)
    ser.write(cmd + b"\r\n")


def gt_getmd():
    gt_sendcmd(b"GT+GETMD")


def gt_getpwd():
    gt_sendcmd(b"GT+GETPWD")


def gt_load1():
    gt_sendcmd(b"GT+GTLOAD=1")


def cmd_callback(line: bytes):
    print("line=%s" % line)
    if line == "GT: READY":
        gt_info()
    elif line == b'+GETDEV: "RC-4000"':
        log.debug("found rc-4000")
    elif line.startswith(b"+REB: "):
        log.debug("rebooting")
    elif line.startswith(b"+GTINCALL: "):
        phone = line.replace(b"+GTINCALL: ", b"")
        log.debug("in call from %s", phone)

        if phone in addressbook():
            gt_load1()

    elif line.startswith(b"+GT: CALL DIS"):
        log.debug("in call ended")
    elif line == b"+GTLOAD: 1":
        log.debug("relay ON")
    elif line == b"+GTLOAD: 0":
        log.debug("relay OFF")
    elif line.startswith(b"+GTWRPN: "):
        phone = line.replace(b"+GTINCALL: ", b"")
        log.debug("new number: %s", phone)
        gt_info()
    elif line.startswith(b"+GETMD: "):
        mode = line.replace(b"+GETMD: ", b"")
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

    elif line.startswith(b"+AUTH: "):
        result = line.replace(b"+AUTH: ", b"")
        if result == b"1":
            log.debug("auth ok")
            gt_info()
            gt_getmd()
            # gt_getpwd()
        else:
            log.debug("auth error")
    elif line.startswith(b"+GTSMS: "):
        sms = line.replace(b"+GTINCALL: ", b"")
        log.debug("in sms: %s", sms)
    else:
        log.error("unknown %s", line)


def main(port: str = "/dev/cu.usbserial-401210", baudrate: int = 115200):
    # Prepare serial connection.
    ser = Serial(
        port,
        baudrate=baudrate,
        bytesize=EIGHTBITS,
        parity=PARITY_NONE,
        stopbits=STOPBITS_ONE,
        timeout=1,
    )

    # ser.flushInput()

    gt_auth(8052)

    line: bytes = b""
    while True:
        b = ser.read(size=1)
        # print("b=%s" % b)
        if not b:
            # empty read
            continue

        if b == b"\r":
            line = line.strip()  # remove "\n"?
            cmd_callback(line)
            line = b""
        else:
            line = line + b


if __name__ == "__main__":
    main()
