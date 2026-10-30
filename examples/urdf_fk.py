"""Minimal NumPy forward kinematics for a serial URDF revolute chain.

Assumes telemetry joint zeros match the URDF zero pose. End-effector frame is
the child link of the last revolute joint (link6 for Leader Arm models).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True, slots=True)
class RevoluteJoint:
    name: str
    xyz: np.ndarray  # (3,)
    rpy: np.ndarray  # (3,) roll, pitch, yaw
    axis: np.ndarray  # (3,) unit axis in joint frame


def _parse_xyz(text: str | None) -> np.ndarray:
    if not text:
        return np.zeros(3, dtype=np.float64)
    return np.fromstring(text, sep=" ", dtype=np.float64)


def _rpy_matrix(rpy: np.ndarray) -> np.ndarray:
    """URDF fixed-axis RPY: R = Rz(yaw) @ Ry(pitch) @ Rx(roll)."""
    roll, pitch, yaw = rpy
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    return np.array(
        [
            [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr],
        ],
        dtype=np.float64,
    )


def _axis_matrix(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues rotation about a unit axis."""
    x, y, z = axis
    c, s = np.cos(angle), np.sin(angle)
    c1 = 1.0 - c
    return np.array(
        [
            [c + x * x * c1, x * y * c1 - z * s, x * z * c1 + y * s],
            [y * x * c1 + z * s, c + y * y * c1, y * z * c1 - x * s],
            [z * x * c1 - y * s, z * y * c1 + x * s, c + z * z * c1],
        ],
        dtype=np.float64,
    )


def _homogeneous(rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    t = np.eye(4, dtype=np.float64)
    t[:3, :3] = rotation
    t[:3, 3] = translation
    return t


def _rotation_to_rpy(rotation: np.ndarray) -> np.ndarray:
    """Inverse of URDF RPY (Rz@Ry@Rx), returns roll, pitch, yaw."""
    pitch = np.arcsin(np.clip(-rotation[2, 0], -1.0, 1.0))
    if abs(rotation[2, 0]) < 0.999999:
        roll = np.arctan2(rotation[2, 1], rotation[2, 2])
        yaw = np.arctan2(rotation[1, 0], rotation[0, 0])
    else:
        # Gimbal lock: yaw ± pitch share one degree of freedom; set yaw = 0.
        roll = np.arctan2(-rotation[0, 1], rotation[1, 1])
        yaw = 0.0
    return np.array([roll, pitch, yaw], dtype=np.float64)


def load_revolute_chain(urdf_path: str | Path) -> list[RevoluteJoint]:
    """Load revolute/continuous joints in document order (serial chain)."""
    root = ET.parse(urdf_path).getroot()
    joints: list[RevoluteJoint] = []
    for node in root.findall("joint"):
        joint_type = node.get("type", "")
        if joint_type not in ("revolute", "continuous"):
            continue
        origin = node.find("origin")
        axis = node.find("axis")
        xyz = _parse_xyz(origin.get("xyz") if origin is not None else None)
        rpy = _parse_xyz(origin.get("rpy") if origin is not None else None)
        axis_vec = _parse_xyz(axis.get("xyz") if axis is not None else "0 0 1")
        norm = np.linalg.norm(axis_vec)
        if norm < 1e-12:
            raise ValueError(f"joint {node.get('name')!r} has zero axis")
        joints.append(
            RevoluteJoint(
                name=node.get("name") or f"joint{len(joints)+1}",
                xyz=xyz,
                rpy=rpy,
                axis=axis_vec / norm,
            )
        )
    if not joints:
        raise ValueError(f"no revolute/continuous joints in {urdf_path}")
    return joints


class ChainFk:
    """Serial-chain FK: base → last revolute child link."""

    def __init__(self, urdf_path: str | Path) -> None:
        self.urdf_path = Path(urdf_path)
        self.joints = load_revolute_chain(self.urdf_path)

    @property
    def dof(self) -> int:
        return len(self.joints)

    def fk(self, q_rad: np.ndarray) -> np.ndarray:
        q = np.asarray(q_rad, dtype=np.float64).reshape(-1)
        if q.shape[0] != self.dof:
            raise ValueError(f"expected {self.dof} joints, got {q.shape[0]}")
        t = np.eye(4, dtype=np.float64)
        for joint, angle in zip(self.joints, q):
            t = t @ _homogeneous(_rpy_matrix(joint.rpy), joint.xyz)
            t = t @ _homogeneous(_axis_matrix(joint.axis, float(angle)), np.zeros(3))
        return t

    def pose_from_degrees(
        self, q_deg: np.ndarray | tuple[float, ...]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (xyz_m, rpy_rad, T_4x4) for the first ``dof`` angles in degrees."""
        q = np.asarray(q_deg, dtype=np.float64).reshape(-1)[: self.dof]
        transform = self.fk(np.deg2rad(q))
        xyz = transform[:3, 3].copy()
        rpy = _rotation_to_rpy(transform[:3, :3])
        return xyz, rpy, transform
