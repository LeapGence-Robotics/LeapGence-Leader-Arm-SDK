"""End-effector pose demo — telemetry + NumPy FK (demo helper, not core SDK).

Reads Joint 1–6 from the arm and computes link6 pose in base_link.
Assumes telemetry zero == URDF zero. Requires numpy and
description/leader_arm_{left,right}/ (URDF + meshes).

  arm.telemetry()  →  angles[0:6]  →  ChainFk(urdf).pose_from_degrees(...)

Side selection:
  1. --urdf path          (highest priority)
  2. --side left|right
  3. get_axis_calib().side

Usage:
  python examples/ee_pose_demo.py
  python examples/ee_pose_demo.py --side left --samples 20
  python examples/ee_pose_demo.py --urdf description/leader_arm_left/urdf/leader_arm_left.urdf
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLES = Path(__file__).resolve().parent
_SRC = _ROOT / "src"
for path in (_SRC, _EXAMPLES):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from leapgence.leader_arm import ArmDevice, ArmSdkError  # noqa: E402


def _fmt_angles(angles: tuple[float, ...]) -> str:
    return "[" + ", ".join(f"{v:7.2f}" for v in angles[:6]) + "]"


def _fmt_vec(values, *, precision: int = 4) -> str:
    return "[" + ", ".join(f"{v:7.{precision}f}" for v in values) + "]"


def _resolve_urdf(side: str | None, urdf_override: str | None) -> tuple[Path, str | None]:
    if urdf_override:
        path = Path(urdf_override)
        return path, side
    if side not in ("left", "right"):
        raise SystemExit("need --side left|right, --urdf, or firmware with get_axis_calib()")
    name = f"leader_arm_{side}"
    return _ROOT / "description" / name / "urdf" / f"{name}.urdf", side


def main() -> int:
    parser = argparse.ArgumentParser(description="Leader Arm end-effector pose demo (NumPy FK)")
    parser.add_argument("--port", default=None, help="COM7 / /dev/ttyACM0; omit to auto-discover")
    parser.add_argument("--samples", type=int, default=10, help="frames to print")
    parser.add_argument("--timeout", type=float, default=2.0, help="seconds to wait for next frame")
    parser.add_argument(
        "--side",
        choices=("left", "right"),
        default=None,
        help="which URDF to load; default = get_axis_calib().side",
    )
    parser.add_argument("--urdf", default=None, help="custom URDF path (overrides --side)")
    args = parser.parse_args()

    try:
        import numpy as np
        from urdf_fk import ChainFk
    except ImportError as exc:
        print(f"needs numpy: {exc}")
        return 1

    print("Leader Arm — end-effector pose demo\n")

    try:
        with ArmDevice(args.port) as arm:
            print(f"connected: {arm.port}")
            print(f"firmware:  v{arm.info().version}")

            side = args.side
            try:
                axis = arm.get_axis_calib()
                print(f"side:      {axis.side}  (from get_axis_calib)")
                if side is None:
                    side = axis.side
            except ArmSdkError as exc:
                print(f"axis:      unavailable ({exc})")

            urdf_path, side = _resolve_urdf(side, args.urdf)
            if not urdf_path.is_file():
                print(f"URDF not found: {urdf_path}")
                return 1

            fk = ChainFk(urdf_path)
            print(f"urdf:      {urdf_path}")
            print(f"fk:        dof={fk.dof}  frame=link6 in base_link  side={side}")
            print("assume:    telemetry zero == URDF zero\n")

            print(f"streaming  ({args.samples} frames)")
            print("   q = Joint 1–6 (deg) → EE xyz (m) + rpy (deg)")
            count = 0
            t0 = time.monotonic()
            for sample in arm.telemetry(timeout=args.timeout):
                count += 1
                xyz, rpy, _ = fk.pose_from_degrees(sample.angles)
                print(
                    f"   [{count:03d}] q={_fmt_angles(sample.angles)}  "
                    f"xyz_m={_fmt_vec(xyz)}  "
                    f"rpy_deg={_fmt_vec(np.rad2deg(rpy), precision=2)}"
                )
                if count >= args.samples:
                    break

            elapsed = time.monotonic() - t0
            rate = count / elapsed if elapsed > 0 else 0.0
            print(f"\ndone: {count} samples in {elapsed:.2f}s (~{rate:.1f} Hz)")
    except ArmSdkError as exc:
        print(f"error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
