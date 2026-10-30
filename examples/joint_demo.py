"""Joint-space demo — core LeapGence Leader Arm SDK usage.

Typical customer flow:

  1. list_serial_ports() / find_port()
  2. with ArmDevice() as arm:
  3. arm.info() / get_home() / get_axis_calib()
  4. arm.set_force(...)                 # optional, 0–255 vibration
  5. for sample in arm.telemetry(...):  # Joint 1–6 + gripper + keys

For end-effector pose (NumPy FK), see ee_pose_demo.py.

Usage:
  python examples/joint_demo.py
  python examples/joint_demo.py --port /dev/ttyACM0 --samples 20 --force 32
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from leapgence.leader_arm import (  # noqa: E402
    ArmDevice,
    ArmSdkError,
    find_port,
    list_serial_ports,
)


def _fmt_angles(angles: tuple[float, ...]) -> str:
    return "[" + ", ".join(f"{v:7.2f}" for v in angles) + "]"


def main() -> int:
    parser = argparse.ArgumentParser(description="Leader Arm joint telemetry demo (core SDK)")
    parser.add_argument("--port", default=None, help="COM7 / /dev/ttyACM0; omit to auto-discover")
    parser.add_argument("--samples", type=int, default=10, help="telemetry frames to print")
    parser.add_argument("--force", type=int, default=0, help="vibration 0–255 while sampling")
    parser.add_argument("--timeout", type=float, default=2.0, help="seconds to wait for next frame")
    args = parser.parse_args()

    print("Leader Arm — joint demo (core SDK)\n")

    # 1) Discover
    print("1) Discover serial ports  [list_serial_ports]")
    ports = list_serial_ports()
    if not ports:
        print("   (none)")
    else:
        for item in ports:
            mark = "  ← Leader Arm" if (item.vid == 0x0483 and item.pid == 0x5740) else ""
            print(f"   {item.device:12s}  {item.description}{mark}")

    # 2) Select port
    print("\n2) Select Leader Arm port  [find_port]")
    try:
        selected = find_port(args.port)
    except ArmSdkError as exc:
        print(f"   error: {exc}")
        return 1
    print(f"   using {selected.device}")

    # 3–5) Connect and use
    try:
        print("\n3) Open device  [with ArmDevice(...) as arm]")
        with ArmDevice(selected.device) as arm:
            print(f"   connected={arm.connected}  port={arm.port}")

            print("\n4) Read device state")
            info = arm.info()
            print(f"   info()            firmware v{info.version}")

            home = arm.get_home()
            print(f"   get_home()        {_fmt_angles(home.offsets)}  (deg)")

            try:
                axis = arm.get_axis_calib()
                print(
                    f"   get_axis_calib()  side={axis.side}  "
                    f"signs={list(axis.signs)}  "
                    f"travel={axis.trigger_travel:.1f}  "
                    f"signed={axis.trigger_signed}"
                )
            except ArmSdkError as exc:
                print(f"   get_axis_calib()  unavailable ({exc})  # needs firmware ≥ v1.0.2")

            force = max(0, min(255, args.force))
            if force:
                print(f"\n5) Force feedback  [set_force({force})]")
                arm.set_force(force)
            else:
                print("\n5) Force feedback  [skipped — --force 0]")

            print(f"\n6) Stream joints  [telemetry(timeout={args.timeout})]  ({args.samples} frames)")
            print("   angles: Joint 1, 2, 3, 4, 5, 6, gripper  (degrees)")
            count = 0
            t0 = time.monotonic()
            try:
                for sample in arm.telemetry(timeout=args.timeout):
                    count += 1
                    print(
                        f"   [{count:03d}] angles={_fmt_angles(sample.angles)}  "
                        f"keys={sample.keys}"
                    )
                    if count >= args.samples:
                        break
            finally:
                if force:
                    arm.set_force(0)
                    print("   set_force(0)")

            elapsed = time.monotonic() - t0
            rate = count / elapsed if elapsed > 0 else 0.0
            print(f"\n   done: {count} samples in {elapsed:.2f}s (~{rate:.1f} Hz)")
    except ArmSdkError as exc:
        print(f"\nerror: {exc}")
        return 1

    print("\nclosed  [context exit → close()]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
