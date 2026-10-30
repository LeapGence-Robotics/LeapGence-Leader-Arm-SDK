"""Print live joint telemetry and device health."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from leapgence.leader_arm import ArmDevice, DeviceTimeoutError  # noqa: E402


with ArmDevice() as arm:
    print("connected:", arm.port)
    try:
        print("firmware:", arm.info().to_dict())
    except DeviceTimeoutError as exc:
        print(f"firmware: unavailable ({exc})")
    arm.on_health(lambda health: print("health:", health.to_dict()))
    for sample in arm.telemetry(timeout=2.0):
        print(sample.to_dict())
