#!/usr/bin/env bash
# Grant the current user access to LeapGence Leader Arm (USB 0483:5740).
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This script is for Linux only." >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  exec sudo --preserve-env=SUDO_USER "$0" "$@"
fi

TARGET_USER="${SUDO_USER:-$USER}"
if [[ -z "$TARGET_USER" || "$TARGET_USER" == "root" ]]; then
  echo "Run this script as a normal user (it will ask for sudo)." >&2
  exit 1
fi

RULE_PATH=/etc/udev/rules.d/99-leader-arm.rules
RULE='SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", MODE="0666", GROUP="dialout", TAG+="uaccess"'

printf '%s\n' "$RULE" >"$RULE_PATH"
chmod 644 "$RULE_PATH"
udevadm control --reload-rules
udevadm trigger

if id -nG "$TARGET_USER" | grep -qw dialout; then
  echo "udev rule installed. $TARGET_USER is already in the dialout group."
else
  usermod -aG dialout "$TARGET_USER"
  echo "udev rule installed. Added $TARGET_USER to the dialout group."
  echo "Log out and back in if the port is still denied."
fi

echo "Unplug and replug the Leader Arm, then try again."
