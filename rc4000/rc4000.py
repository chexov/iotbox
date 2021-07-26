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


class RCMode(Enum):
    NORMAL: int = 0
    ACCESS: int = 1
    DOOR: int = 2
    UNKNOWN: int = 3


class DeviceState:
    rcmode: RCMode
    pin: int


class SIMSerialClient:
    def __init__(self, port: str, baudrate: int, authpin: int = 1111):
        self._ser = Serial(
            port,
            baudrate=baudrate,
            bytesize=EIGHTBITS,
            parity=PARITY_NONE,
            stopbits=STOPBITS_ONE,
            timeout=1,
        )
        # self._ser.flushInput()
        self.state = DeviceState()
        self.state.pin = authpin

    def cmd_callback(self, line: bytes):
        print("line=%s" % line)
        if line == "GT: READY":
            self.gt_info()
        elif line == b'+GETDEV: "RC-4000"':
            self.on_getdev()
        elif line.startswith(b"+REB: "):
            self.on_reboot()
        elif line.startswith(b"+GTINCALL: "):
            phone = line.replace(b"+GTINCALL: ", b"")
            self.on_incall(phone)
        elif line.startswith(b"+GT: CALL DIS"):
            self.on_callend()
        elif line == b"+GTLOAD: 1":
            self.on_loadon()
        elif line == b"+GTLOAD: 0":
            self.on_loadoff()
        elif line.startswith(b"+GTWRPN: "):
            phone = line.replace(b"+GTINCALL: ", b"")
            log.debug("new number: %s", phone)
            self.gt_info()
        elif line.startswith(b"+GETMD: "):
            mode = line.replace(b"+GETMD: ", b"")
            self.on_getmd(mode)

        elif line.startswith(b"+AUTH: "):
            result = line.replace(b"+AUTH: ", b"")
            self.on_auth(result)
        elif line.startswith(b"+GTSMS: "):
            sms = line.replace(b"+GTINCALL: ", b"")
            self.on_sms(sms)
        else:
            log.error("unknown %s", line)

    def gt_auth(self, pin: int):
        self.gt_sendcmd(b"GT+AUTH=%s" % pin)

    def gt_info(self):
        self.gt_sendcmd(b"GT+INFO")

    def gt_sendcmd(self, cmd: bytes):
        log.debug("sending '%s'", cmd)
        self._ser.write(cmd + b"\r\n")

    def gt_getmd(self):
        self.gt_sendcmd(b"GT+GETMD")

    def gt_getpwd(self):
        self.gt_sendcmd(b"GT+GETPWD")

    def gt_load1(self):
        self.gt_sendcmd(b"GT+GTLOAD=1")

    def on_sms(self, sms):
        log.debug("in sms: %s", sms)

    def on_auth(self, result):
        if result == b"1":
            log.debug("auth ok")
            self.gt_info()
            self.gt_getmd()
            # gt_getpwd()
        else:
            log.debug("auth error")

    def on_getmd(self, mode):
        log.debug("mode is %s", mode)
        try:
            log.debug(RCMode(value=int(mode)))
        except ValueError:
            log.debug("mode is UNKNOWN")

    def on_loadoff(self):
        log.debug("relay OFF")

    def on_loadon(self):
        log.debug("relay ON")

    def on_callend(self):
        log.debug("in call ended")

    def on_incall(self, phone):
        log.debug("in call from %s", phone)
        if phone in addressbook():
            self.gt_load1()

    def on_reboot(self):
        log.debug("rebooting")

    def on_getdev(self):
        log.debug("found rc-4000")

    def loop(self):
        line: bytes = b""
        while True:
            b = self._ser.read(size=1)
            # print("b=%s" % b)
            if not b:
                # empty read on timeout
                continue

            if b == b"\r":
                line = line.strip()  # remove "\n"?
                if not line:
                    continue

                self.cmd_callback(line)
                line = b""
            else:
                line = line + b


def main(port: str = "/dev/cu.usbserial-401210", baudrate: int = 115200):
    simcli = SIMSerialClient(port=port, baudrate=baudrate, authpin=8042)
    simcli.gt_auth(8052)
    simcli.loop()


if __name__ == "__main__":
    main()
