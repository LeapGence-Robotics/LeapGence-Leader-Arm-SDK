# Leader Arm Python SDK

## 能力概览

Leader Arm 是一款面向机器人遥操作的通用主臂，适配市面上绝大部分 6 轴机械臂：


| 能力    | 说明                     |
| ----- | ---------------------- |
| 广泛适配  | 标准关节映射，兼容主流 6 轴机械臂     |
| 高频通讯  | 采样率 100Hz 以上，低延迟读取     |
| 力控反馈  | 支持振动反馈，用于操作提示与触觉交互     |
| 双模式控制 | 支持 TCP（末端位姿）与关节角两种控制方式 |
| 多系统支持 | 支持 Windows、Linux、macOS |


## 目录

- [安装](#安装)
- [连接设备](#连接设备)
- [回零与校准](#回零与校准)
- [读取关节与按键](#读取关节与按键)
- [力反馈](#力反馈)
- [示例](#示例)
- [遇到问题](#遇到问题)
- [许可](#许可)

## 安装

需要 Python 3.10 或更高版本。从 [GitHub Releases](https://github.com/LeapGence-Robotics/LeapGence-Leader-Arm-SDK/releases) 下载 wheel 后安装：

```bash
python -m pip install leapgence_leader_arm-1.0.0-py3-none-any.whl
```

Linux 首次使用时，若已克隆仓库：

```bash
bash scripts/install-linux-udev.sh
```

脚本会写入 udev 规则、刷新设备，并把当前用户加入 `dialout` 组。仅 pip 安装时，把下面一行写入 `/etc/udev/rules.d/99-leader-arm.rules` 后执行 `sudo udevadm control --reload-rules && sudo udevadm trigger`，并将用户加入 `dialout` 组：

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", MODE="0666", GROUP="dialout", TAG+="uaccess"
```

然后重新插拔设备；若仍无权限，请重新登录后再试。

## 连接设备

插入 Leader Arm 后，SDK 会按 USB 标识自动发现串口。也可以指定端口：

```python
from leapgence.leader_arm import ArmDevice, list_serial_ports

print(list_serial_ports())

with ArmDevice("COM7") as arm:                 # Windows
    print(arm.port, arm.info().version)

with ArmDevice("/dev/ttyACM0") as arm:         # Linux
    print(arm.port, arm.info().version)

with ArmDevice("/dev/cu.usbmodem1101") as arm:  # macOS
    print(arm.port, arm.info().version)
```

## 回零与校准

设备出厂通常已设好 Home。仅在需要重新定义零位时再调用 `set_home()`；日常读取用 `get_home()` 即可。`clear_home()` 会清除已保存偏移，请谨慎使用。

```python
print(arm.get_home())
# arm.set_home()    # 仅在需要重新设零时使用
# arm.clear_home()  # 会清除已保存偏移
```

极性、扳机行程和左右臂保存在设备中，可用 `get_axis_calib()` 读取（固件 **v1.0.2** 或更高版本）：

```python
print(arm.get_axis_calib())
```

## 读取关节与按键

遥测包含 7 个角度（度）和 2 个按键状态。`angles` 顺序为 Joint 1、Joint 2、Joint 3、Joint 4、Joint 5、Joint 6、夹爪。`timestamp` 为本机收包时间（毫秒）。`timeout` 是等待下一帧的秒数：

```python
from leapgence.leader_arm import ArmDevice

with ArmDevice() as arm:
    for sample in arm.telemetry(timeout=2):
        print(sample.angles, sample.keys)
```

也可以用 `arm.on_telemetry(...)` 在后台持续接收。

## 力反馈

力反馈以振动实现。`set_force` 设置强度，范围为 0–255（`0` 关闭，`255` 最强）。数值会立即排队下发，不会阻塞你的主循环：

```python
arm.set_force(64)
```

## 示例

- `examples/joint_demo.py`：发现设备、读取信息与关节遥测（核心 SDK 用法）
- `examples/ee_pose_demo.py`：关节角 → 末端位姿（demo 用 NumPy FK）
- `examples/monitor.py`：持续打印关节数据

```bash
python examples/joint_demo.py
python examples/joint_demo.py --port COM7 --samples 20 --force 32
python examples/ee_pose_demo.py --samples 20
```

## 遇到问题


| 情况                | 处理                                                                                      |
| ----------------- | --------------------------------------------------------------------------------------- |
| 找不到设备             | 确认 USB 已连接，Windows 查看设备管理器中的 COM 口，Linux 查看 `/dev/ttyACM*`，macOS 查看 `/dev/cu.usbmodem*` |
| Linux 打开失败或读取版本超时 | 先配置 udev 并重新插拔；如系统装了 ModemManager，请避免它占用该串口                                             |
| 校准接口不可用           | 确认设备固件为 v1.0.2 或更高版本                                                                    |


连接和通信失败会抛出 `ArmSdkError` 的子类，便于按类型处理。

## 许可

本软件以 [MIT License](LICENSE) 发布。

Copyright © 2026 阶跃致能（北京）机器人科技有限公司 / LeapGence (Beijing) Robotics Technology Co., Ltd.