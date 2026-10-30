"""Pure protocol codecs; this module has no hardware dependencies."""

from __future__ import annotations

import math
import struct
import time

from .constants import MAX_PAYLOAD, Command
from .errors import ProtocolError
from .models import (
    DeviceHealth,
    Frame,
    FwInfo,
    AxisCalib,
    HomeOffsets,
    Telemetry,
)


def checksum(data: bytes | bytearray | memoryview, init: int = 0xFFFFFFFF) -> int:
    acc = init & 0xFFFFFFFF
    for value in data:
        acc ^= value
        for _ in range(8):
            acc = ((acc >> 1) ^ 0xEDB88320) if acc & 1 else acc >> 1
    return (acc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def build_frame(command: int, payload: bytes = b"") -> bytes:
    if not 0 <= int(command) <= 0xFF:
        raise ValueError("command must fit in one byte")
    if len(payload) > MAX_PAYLOAD:
        raise ValueError(f"payload exceeds {MAX_PAYLOAD} bytes")
    body = struct.pack("<BH", int(command), len(payload)) + payload
    return body + struct.pack("<I", checksum(body))


class FrameParser:
    """Incremental, resynchronizing parser for framed control traffic."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def reset(self) -> None:
        self.buffer.clear()

    def feed(self, data: bytes | bytearray | memoryview) -> list[Frame]:
        self.buffer.extend(data)
        frames: list[Frame] = []
        while len(self.buffer) >= 3:
            payload_len = self.buffer[1] | self.buffer[2] << 8
            if payload_len > MAX_PAYLOAD:
                del self.buffer[0]
                continue
            total = 3 + payload_len + 4
            if len(self.buffer) < total:
                break
            candidate = bytes(self.buffer[:total])
            body = candidate[:-4]
            expected = struct.unpack_from("<I", candidate, total - 4)[0]
            if checksum(body) != expected:
                del self.buffer[0]
                continue
            frames.append(Frame(candidate[0], candidate[3:-4]))
            del self.buffer[:total]
        return frames


class DeviceFrameParser(FrameParser):
    """Inbound parser that also discards interleaved 32-byte telemetry."""

    _INBOUND_COMMANDS = {
        int(Command.ACK),
        int(Command.NAK),
    }

    def feed(self, data: bytes | bytearray | memoryview) -> list[Frame]:
        self.buffer.extend(data)
        frames: list[Frame] = []
        while len(self.buffer) >= 3:
            if self.buffer[0] == 0xFA:
                if len(self.buffer) < TelemetryParser.FRAME_SIZE:
                    break
                if self.buffer[31] == 0xAF:
                    del self.buffer[: TelemetryParser.FRAME_SIZE]
                    continue
                del self.buffer[0]
                continue
            if self.buffer[0] == 0xFB:
                if len(self.buffer) < TelemetryParser.HEALTH_SIZE:
                    break
                if self.buffer[TelemetryParser.HEALTH_SIZE - 1] == 0xBF:
                    del self.buffer[: TelemetryParser.HEALTH_SIZE]
                    continue
                del self.buffer[0]
                continue
            if self.buffer[0] not in self._INBOUND_COMMANDS:
                del self.buffer[0]
                continue
            payload_len = self.buffer[1] | self.buffer[2] << 8
            if payload_len > MAX_PAYLOAD:
                del self.buffer[0]
                continue
            total = 3 + payload_len + 4
            if len(self.buffer) < total:
                break
            candidate = bytes(self.buffer[:total])
            body = candidate[:-4]
            expected = struct.unpack_from("<I", candidate, total - 4)[0]
            if checksum(body) != expected:
                del self.buffer[0]
                continue
            frames.append(Frame(candidate[0], candidate[3:-4]))
            del self.buffer[:total]
        return frames


class TelemetryParser:
    FRAME_SIZE = 32
    HEALTH_SIZE = 8

    def __init__(self) -> None:
        self.buffer = bytearray()
        self._health: list[DeviceHealth] = []

    def reset(self) -> None:
        self.buffer.clear()
        self._health.clear()

    def pop_health(self) -> list[DeviceHealth]:
        items, self._health = self._health, []
        return items

    @staticmethod
    def _parse_health(frame: bytes) -> DeviceHealth:
        return DeviceHealth(
            expected=frame[1],
            live=frame[2],
            arm_node=bool(frame[3] & 0x01),
            online=frame[4],
            enc_ok=frame[5],
        )

    def feed(
        self, data: bytes | bytearray | memoryview, *, timestamp: float | None = None
    ) -> list[Telemetry]:
        self.buffer.extend(data)
        output: list[Telemetry] = []
        stamp = time.time() * 1000.0 if timestamp is None else timestamp
        while self.buffer:
            head = self.buffer[0]
            if head == 0xFB:
                if len(self.buffer) < self.HEALTH_SIZE:
                    break
                if self.buffer[self.HEALTH_SIZE - 1] == 0xBF:
                    health = self._parse_health(bytes(self.buffer[: self.HEALTH_SIZE]))
                    self._health.append(health)
                    if output:
                        last = output[-1]
                        output[-1] = Telemetry(
                            last.angles, last.keys, last.timestamp, health
                        )
                    del self.buffer[: self.HEALTH_SIZE]
                    continue
                del self.buffer[0]
                continue
            if head == 0xFA:
                if len(self.buffer) < self.FRAME_SIZE:
                    break
                if self.buffer[self.FRAME_SIZE - 1] == 0xAF:
                    values = struct.unpack_from("<7f2B", self.buffer, 1)
                    output.append(
                        Telemetry(
                            angles=tuple(values[:7]),  # type: ignore[arg-type]
                            keys=(values[7], values[8]),
                            timestamp=stamp,
                        )
                    )
                    del self.buffer[: self.FRAME_SIZE]
                    continue
                del self.buffer[0]
                continue
            fa = self.buffer.find(0xFA)
            fb = self.buffer.find(0xFB)
            start = min(i for i in (fa, fb) if i >= 0) if (fa >= 0 or fb >= 0) else -1
            if start < 0:
                self.buffer.clear()
                break
            del self.buffer[:start]
        return output


def force_packet(force: float | int) -> bytes:
    value = max(0, min(255, round(force)))
    return bytes((0x1A, value, 0xA1))


def parse_fw_info(payload: bytes) -> FwInfo:
    if len(payload) < 16:
        return FwInfo(0, 0, 0)
    _role_raw, major, minor, patch, _product_id, _app_start = struct.unpack_from(
        "<IHHHHI", payload
    )
    return FwInfo(major, minor, patch)


def parse_home_offsets(payload: bytes) -> HomeOffsets:
    if len(payload) < 28:
        raise ProtocolError(f"Home payload too short: {len(payload)}")
    return HomeOffsets(struct.unpack_from("<7f", payload))


def _as_sign(value: int) -> int:
    return -1 if int(value) < 0 else 1


def parse_axis_calib(payload: bytes) -> AxisCalib:
    if len(payload) < 12:
        raise ProtocolError(f"Axis calib payload too short: {len(payload)}")
    raw = struct.unpack_from("<7bBf", payload)
    signs = tuple(_as_sign(v) for v in raw[:7])
    travel = float(raw[8])
    if not math.isfinite(travel):
        travel = 53.0
    travel = min(90.0, max(28.0, travel))
    flags = int(raw[7])
    return AxisCalib(
        (
            signs[0],
            signs[1],
            signs[2],
            signs[3],
            signs[4],
            signs[5],
            signs[6],
        ),
        bool(flags & 0x01),
        travel,
        "right" if flags & 0x02 else "left",
    )
