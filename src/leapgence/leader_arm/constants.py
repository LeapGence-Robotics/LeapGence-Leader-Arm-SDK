"""Wire-level constants shared by the SDK."""

from enum import IntEnum


class Command(IntEnum):
    ACK = 0x10
    NAK = 0x11
    INFO = 0x30
    SET_HOME = 0x31
    GET_HOME = 0x32
    CLEAR_HOME = 0x33
    GET_AXIS_CALIB = 0x35


MAX_PAYLOAD = 64
DEFAULT_BAUDRATE = 115200
USB_VID = 0x0483
USB_PID = 0x5740
