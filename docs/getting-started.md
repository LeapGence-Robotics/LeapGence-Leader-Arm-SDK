# 开始使用 {#getting-started}

## 安装 {#install}

需要 Python 3.10 或更高版本。从 [GitHub Releases](https://github.com/LeapGence-Robotics/LeapGence-Leader-Arm-SDK/releases) 下载 wheel 后安装：

```bash
python -m pip install leapgence_leader_arm-1.0.0-py3-none-any.whl
```

## Linux 权限 {#linux}

克隆仓库后可执行：

```bash
bash scripts/install-linux-udev.sh
```

脚本会写入 udev 规则、刷新设备，并把当前用户加入 `dialout` 组。若只通过 pip 安装、没有仓库，可自行写入 `/etc/udev/rules.d/99-leader-arm.rules`：

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", MODE="0666", GROUP="dialout", TAG+="uaccess"
```

然后 `sudo udevadm control --reload-rules && sudo udevadm trigger`，并把用户加入 `dialout` 组。重新插拔设备；若仍无权限，请重新登录后再试。

## 第一次连接 {#first-connect}

插入 Leader Arm 后，SDK 会按 USB 标识自动发现串口：

```python
from leapgence.leader_arm import ArmDevice

with ArmDevice() as arm:
    print(arm.port, arm.info().version)
    sample = next(arm.telemetry(timeout=2))
    print(sample.angles, sample.keys)
```

也可以指定端口，详见 [连接设备](guide/connect.md)。

## 接下来 {#next}

- [读取关节与按键](guide/telemetry.md)
- [下发力反馈](guide/force.md)
- [回零与校准](guide/calibration.md)
