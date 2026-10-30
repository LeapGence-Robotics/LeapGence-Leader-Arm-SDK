"""Typed public data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class PortInfo:
    device: str
    description: str = ""
    hwid: str = ""
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Frame:
    command: int
    payload: bytes


@dataclass(frozen=True, slots=True)
class DeviceHealth:
    expected: int
    live: int
    arm_node: bool
    online: int
    enc_ok: int

    def to_dict(self) -> dict[str, object]:
        return {
            "expected": self.expected,
            "live": self.live,
            "armNode": self.arm_node,
            "online": self.online,
            "encOk": self.enc_ok,
        }


@dataclass(frozen=True, slots=True)
class Telemetry:
    """Live sample. ``angles`` is Joint 1–6 then gripper, in degrees.

    ``timestamp`` is host receive time in milliseconds. ``health`` is often
    None unless a health packet arrived with the sample.
    """

    angles: tuple[float, float, float, float, float, float, float]
    keys: tuple[int, int]
    timestamp: float
    health: DeviceHealth | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "angles": list(self.angles),
            "keys": list(self.keys),
            "t": self.timestamp,
        }
        if self.health is not None:
            payload["health"] = self.health.to_dict()
        return payload


@dataclass(frozen=True, slots=True)
class FwInfo:
    major: int
    minor: int
    patch: int

    @property
    def version(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_dict(self) -> dict[str, object]:
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class HomeOffsets:
    """Home offsets in degrees, same order as ``Telemetry.angles``."""

    offsets: tuple[float, float, float, float, float, float, float]

    def to_dict(self) -> dict[str, object]:
        return {"offsets": list(self.offsets)}


@dataclass(frozen=True, slots=True)
class AxisCalib:
    """Device-stored polarity (Joint 1–6 + gripper), trigger travel, and arm side."""

    signs: tuple[int, int, int, int, int, int, int]
    trigger_signed: bool
    trigger_travel: float
    side: str = "left"

    def to_dict(self) -> dict[str, object]:
        return {
            "signs": list(self.signs),
            "triggerSigned": self.trigger_signed,
            "triggerTravel": self.trigger_travel,
            "side": self.side,
        }
