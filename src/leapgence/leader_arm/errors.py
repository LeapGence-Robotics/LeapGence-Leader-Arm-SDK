"""Public SDK exception hierarchy."""


class ArmSdkError(Exception):
    """Base class for all expected SDK failures."""


class PortNotFoundError(ArmSdkError):
    """No matching serial port was found."""


class TransportError(ArmSdkError):
    """Serial transport failed or disconnected."""


class ProtocolError(ArmSdkError):
    """A malformed or unexpected wire response was received."""


class DeviceTimeoutError(TransportError, TimeoutError):
    """A device operation did not complete before its deadline."""


class DeviceRejectedError(ProtocolError):
    """The device returned a NAK."""

    def __init__(self, operation: str, status: int) -> None:
        self.operation = operation
        self.status = status
        super().__init__(f"{operation}: NAK status=0x{status:02X}")
