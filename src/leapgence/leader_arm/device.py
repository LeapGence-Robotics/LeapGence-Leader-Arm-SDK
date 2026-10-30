"""High-level synchronous API for LeapGence Leader Arm devices."""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Iterator

from .constants import Command
from .errors import (
    DeviceRejectedError,
    DeviceTimeoutError,
    TransportError,
)
from .models import (
    DeviceHealth,
    FwInfo,
    AxisCalib,
    HomeOffsets,
    Telemetry,
)
from .protocol import (
    DeviceFrameParser,
    TelemetryParser,
    build_frame,
    force_packet,
    parse_axis_calib,
    parse_fw_info,
    parse_home_offsets,
)
from .transport import SerialTransport, find_port

TelemetryCallback = Callable[[Telemetry], None]
HealthCallback = Callable[[DeviceHealth], None]
DisconnectCallback = Callable[[Exception | None], None]


class ArmDevice:
    """Thread-safe, blocking API with background telemetry dispatch."""

    def __init__(
        self,
        port: str | None = None,
        *,
        transport_factory: Callable[[str], SerialTransport] = SerialTransport,
    ) -> None:
        self.port = port
        self._transport_factory = transport_factory
        self._transport: SerialTransport | None = None
        self._stop = threading.Event()
        self._reader: threading.Thread | None = None
        self._mode = "monitor"
        self._mode_lock = threading.RLock()
        self._request_lock = threading.Lock()
        self._frames: queue.Queue[tuple[int, bytes]] = queue.Queue()
        self._frame_parser = DeviceFrameParser()
        self._telemetry_parser = TelemetryParser()
        self._telemetry_handlers: list[TelemetryCallback] = []
        self._health_handlers: list[HealthCallback] = []
        self._disconnect_handlers: list[DisconnectCallback] = []
        self._force = 0
        self._force_sent = -1
        self._force_stop = threading.Event()
        self._force_thread: threading.Thread | None = None

    @property
    def connected(self) -> bool:
        return bool(self._transport and self._transport.is_open)

    def open(self, port: str | None = None) -> str:
        self.close()
        selected = find_port(port or self.port).device
        transport = self._transport_factory(selected)
        transport.open()
        self.port = selected
        self._transport = transport
        self._stop.clear()
        self._mode = "monitor"
        self._reader = threading.Thread(target=self._read_loop, name="arm-sdk-reader", daemon=True)
        self._reader.start()
        self._start_force_loop()
        return selected

    def close(self) -> None:
        self._stop.set()
        self._force_stop.set()
        transport, self._transport = self._transport, None
        if transport:
            transport.close()
        if self._reader and self._reader is not threading.current_thread():
            self._reader.join(timeout=1.0)
        if self._force_thread and self._force_thread is not threading.current_thread():
            self._force_thread.join(timeout=0.2)
        self._reader = None
        self._force_thread = None
        self._clear_parsers()

    def __enter__(self) -> ArmDevice:
        self.open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def on_telemetry(self, callback: TelemetryCallback) -> Callable[[], None]:
        self._telemetry_handlers.append(callback)
        return lambda: self._remove(self._telemetry_handlers, callback)

    def on_health(self, callback: HealthCallback) -> Callable[[], None]:
        self._health_handlers.append(callback)
        return lambda: self._remove(self._health_handlers, callback)

    def on_disconnect(self, callback: DisconnectCallback) -> Callable[[], None]:
        self._disconnect_handlers.append(callback)
        return lambda: self._remove(self._disconnect_handlers, callback)

    @staticmethod
    def _remove(items: list, callback: object) -> None:
        try:
            items.remove(callback)
        except ValueError:
            pass

    def telemetry(self, timeout: float | None = None) -> Iterator[Telemetry]:
        samples: queue.Queue[Telemetry] = queue.Queue()
        remove = self.on_telemetry(samples.put)
        try:
            while self.connected:
                try:
                    yield samples.get(timeout=timeout)
                except queue.Empty as exc:
                    raise DeviceTimeoutError("telemetry timeout") from exc
        finally:
            remove()

    def set_force(self, force: int | float) -> int:
        """Queue force-feedback vibration intensity 0–255 (0 = off). Does not block."""
        self._force = max(0, min(255, round(force)))
        # Best-effort immediate write; background loop retries including 0.
        if self._request_lock.acquire(blocking=False):
            try:
                if self.connected and self._mode == "monitor":
                    self._write(force_packet(self._force))
                    self._force_sent = self._force
            except TransportError:
                pass
            finally:
                self._request_lock.release()
        return self._force

    def info(self, timeout: float = 3.0, *, attempts: int = 3) -> FwInfo:
        payload = self._control_retry(
            Command.INFO,
            timeout=timeout,
            strip_command=True,
            attempts=attempts,
        )
        return parse_fw_info(payload)

    def probe(self, timeout: float = 0.8) -> FwInfo:
        """Single-shot INFO used to reject unrelated serial ports quickly."""
        return self.info(timeout=timeout, attempts=1)

    def set_home(self, timeout: float = 5.0) -> HomeOffsets:
        return parse_home_offsets(
            self._control_retry(Command.SET_HOME, timeout=timeout)
        )

    def get_home(self, timeout: float = 3.0) -> HomeOffsets:
        return parse_home_offsets(
            self._control_retry(Command.GET_HOME, timeout=timeout)
        )

    def clear_home(self, timeout: float = 5.0) -> HomeOffsets:
        return parse_home_offsets(
            self._control_retry(Command.CLEAR_HOME, timeout=timeout)
        )

    def get_axis_calib(self, timeout: float = 3.0) -> AxisCalib:
        return parse_axis_calib(
            self._control_retry(Command.GET_AXIS_CALIB, timeout=timeout)
        )

    def _control(
        self,
        command: int,
        payload: bytes = b"",
        *,
        timeout: float,
        strip_command: bool = False,
    ) -> bytes:
        previous = self._mode
        try:
            self._set_mode("control")
            # Drop in-flight 200Hz telemetry before asking for ACK responses.
            self._drain()
            data = self._exchange(command, payload, timeout=timeout)
            if strip_command and len(data) >= 17 and data[0] == command:
                data = data[1:]
            return data
        finally:
            self._set_mode(previous)

    def _control_retry(
        self,
        command: int,
        payload: bytes = b"",
        *,
        timeout: float,
        strip_command: bool = False,
        attempts: int = 3,
    ) -> bytes:
        last_error: Exception | None = None
        for attempt in range(max(1, attempts)):
            try:
                return self._control(
                    command,
                    payload,
                    timeout=timeout,
                    strip_command=strip_command,
                )
            except DeviceTimeoutError as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                time.sleep(0.05)
        assert last_error is not None
        raise last_error

    def _exchange(
        self, command: int, payload: bytes = b"", timeout: float = 5.0
    ) -> bytes:
        with self._request_lock:
            self._clear_frame_queue()
            self._write(build_frame(command, payload))
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise DeviceTimeoutError(f"command 0x{int(command):02X} timeout")
                try:
                    response, data = self._frames.get(timeout=remaining)
                except queue.Empty as exc:
                    raise DeviceTimeoutError(f"command 0x{int(command):02X} timeout") from exc
                if response == Command.ACK:
                    return data
                if response == Command.NAK:
                    status = data[1] if len(data) >= 2 and data[0] == int(command) else data[0] if data else 0xFF
                    raise DeviceRejectedError(f"command 0x{int(command):02X}", status)

    def _set_mode(self, mode: str) -> None:
        with self._mode_lock:
            self._mode = mode
            self._frame_parser.reset()
            self._telemetry_parser.reset()

    def _drain(self) -> None:
        self._clear_frame_queue()
        if self._transport:
            self._transport.reset_input_buffer()
        # Brief pause so leftover telemetry does not collide with the next command.
        time.sleep(0.02)
        if self._transport:
            self._transport.reset_input_buffer()
        self._clear_frame_queue()
        time.sleep(0.05)

    def _clear_frame_queue(self) -> None:
        while True:
            try:
                self._frames.get_nowait()
            except queue.Empty:
                break

    def _clear_parsers(self) -> None:
        self._frame_parser.reset()
        self._telemetry_parser.reset()
        self._clear_frame_queue()

    def _write(self, data: bytes) -> None:
        transport = self._transport
        if not transport or not transport.is_open:
            raise TransportError("device is not open")
        transport.write(data)

    def _read_loop(self) -> None:
        error: Exception | None = None
        try:
            while not self._stop.is_set():
                transport = self._transport
                if not transport:
                    break
                chunk = transport.read()
                if not chunk:
                    continue
                with self._mode_lock:
                    mode = self._mode
                    if mode == "monitor":
                        for sample in self._telemetry_parser.feed(chunk):
                            for callback in tuple(self._telemetry_handlers):
                                callback(sample)
                        for health in self._telemetry_parser.pop_health():
                            for callback in tuple(self._health_handlers):
                                callback(health)
                    else:
                        for frame in self._frame_parser.feed(chunk):
                            self._frames.put((frame.command, frame.payload))
        except Exception as exc:
            error = exc
        finally:
            if not self._stop.is_set():
                for callback in tuple(self._disconnect_handlers):
                    callback(error)

    def _start_force_loop(self) -> None:
        self._force_stop.clear()
        self._force_sent = -1

        def run() -> None:
            while not self._force_stop.wait(0.04):
                if not self.connected:
                    continue
                target = self._force
                if target == self._force_sent:
                    continue
                # Serialize against INFO/Home so force bytes cannot corrupt frames.
                if not self._request_lock.acquire(blocking=False):
                    continue
                try:
                    if self._mode == "monitor" and self.connected:
                        self._write(force_packet(target))
                        self._force_sent = target
                except TransportError:
                    return
                finally:
                    self._request_lock.release()

        self._force_thread = threading.Thread(target=run, name="arm-sdk-force", daemon=True)
        self._force_thread.start()
