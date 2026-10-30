"""pyserial transport and deterministic LeapGence Leader Arm port discovery."""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from typing import Any

import serial
from serial.tools import list_ports

from .constants import DEFAULT_BAUDRATE, USB_PID, USB_VID
from .errors import PortNotFoundError, TransportError
from .models import PortInfo

# Opening Bluetooth / ACPI / modem ports can block forever on Windows.
# Includes post-open settle (≤0.8s on Linux).
_OPEN_TIMEOUT_S = 3.0


def list_serial_ports() -> list[PortInfo]:
    return [
        PortInfo(
            device=item.device,
            description=item.description or "",
            hwid=item.hwid or "",
            vid=item.vid,
            pid=item.pid,
            serial_number=item.serial_number,
        )
        for item in list_ports.comports()
    ]


def is_arm_port(port: PortInfo) -> bool:
    """True for a LeapGence Leader Arm USB serial port."""
    if port.vid == USB_VID and port.pid == USB_PID:
        return True
    text = f"{port.description} {port.hwid}".upper().replace(" ", "")
    return "ARMCONTROLLER" in text or "VID:PID=0483:5740" in text or (
        "0483" in text and "5740" in text
    )


def find_port(prefer: str | None = None) -> PortInfo:
    ports = list_serial_ports()
    if prefer:
        for item in ports:
            if item.device.casefold() == prefer.casefold():
                return item
    candidates = [item for item in ports if is_arm_port(item)]
    if candidates:
        return candidates[0]
    summary = [(item.device, item.hwid) for item in ports]
    raise PortNotFoundError(f"no LeapGence Leader Arm port; ports={summary}")


class SerialTransport:
    """Small testable wrapper around ``serial.Serial``."""

    def __init__(
        self,
        port: str,
        *,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = 0.1,
        write_timeout: float = 0.5,
        open_timeout: float = _OPEN_TIMEOUT_S,
        serial_factory: Callable[..., Any] = serial.Serial,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.write_timeout = write_timeout
        self.open_timeout = open_timeout
        self._factory = serial_factory
        self._serial: Any | None = None

    @property
    def is_open(self) -> bool:
        return bool(self._serial and self._serial.is_open)

    def open(self) -> None:
        if self.is_open:
            return
        result: dict[str, Any] = {}

        def _open() -> None:
            try:
                # Keep modem lines quiet so opening the port does not reset the device.
                serial_port = self._factory(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=self.timeout,
                    write_timeout=self.write_timeout,
                    rtscts=False,
                    dsrdtr=False,
                    xonxoff=False,
                )
                try:
                    serial_port.dtr = False
                    serial_port.rts = False
                except Exception:
                    pass
                if hasattr(serial_port, "exclusive"):
                    try:
                        serial_port.exclusive = True
                    except Exception:
                        pass
                # Linux ACM often needs longer settle after open / ModemManager probes.
                settle = 0.8 if sys.platform.startswith("linux") else 0.35
                time.sleep(settle)
                serial_port.reset_input_buffer()
                try:
                    serial_port.reset_output_buffer()
                except Exception:
                    pass
                result["serial"] = serial_port
            except BaseException as exc:  # noqa: BLE001 — marshalled to caller
                result["error"] = exc

        worker = threading.Thread(target=_open, name=f"serial-open-{self.port}", daemon=True)
        worker.start()
        worker.join(self.open_timeout)
        if worker.is_alive():
            raise TransportError(
                f"cannot open {self.port}: timed out after {self.open_timeout:.1f}s"
            )
        if "error" in result:
            exc = result["error"]
            raise TransportError(f"cannot open {self.port}: {exc}") from exc
        self._serial = result.get("serial")
        if self._serial is None:
            raise TransportError(f"cannot open {self.port}: unknown failure")

    def close(self) -> None:
        serial_port, self._serial = self._serial, None
        if serial_port is not None:
            try:
                serial_port.close()
            except Exception:
                pass

    def read(self, size: int = 1) -> bytes:
        if not self._serial:
            raise TransportError("serial port is not open")
        try:
            available = int(self._serial.in_waiting)
            return bytes(self._serial.read(available or size))
        except Exception as exc:
            raise TransportError(f"serial read failed: {exc}") from exc

    def write(self, data: bytes) -> None:
        if not self._serial:
            raise TransportError("serial port is not open")
        try:
            count = self._serial.write(data)
            self._serial.flush()
            if count != len(data):
                raise TransportError(f"short serial write: {count}/{len(data)}")
        except TransportError:
            raise
        except Exception as exc:
            raise TransportError(f"serial write failed: {exc}") from exc

    def reset_input_buffer(self) -> None:
        if self._serial:
            self._serial.reset_input_buffer()

    def __enter__(self) -> SerialTransport:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
