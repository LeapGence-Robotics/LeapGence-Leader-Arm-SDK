# 故障排除 {#troubleshooting}

| 情况 | 处理 |
|---|---|
| 找不到设备 | 确认 USB 已连接。Windows 查看设备管理器中的 COM 口，Linux 查看 `/dev/ttyACM*`，macOS 查看 `/dev/cu.usbmodem*` |
| Linux 打开失败或读取版本超时 | 先配置 udev（见 [开始使用](getting-started.md#linux)）并重新插拔；如系统装了 ModemManager，请避免它占用该串口 |
| 校准读取不可用 | 确认设备固件为 v1.0.2 或更高版本 |

连接和通信失败会抛出 `ArmSdkError` 的子类，便于按类型处理：

```python
from leapgence.leader_arm import ArmDevice, ArmSdkError, PortNotFoundError

try:
    with ArmDevice() as arm:
        print(arm.info().version)
except PortNotFoundError:
    print("未找到 Leader Arm")
except ArmSdkError as exc:
    print(f"设备错误: {exc}")
```

仍无法连接时，可用 `list_serial_ports()` 确认系统是否枚举到串口，以及 VID/PID 是否为 `0483:5740`。
