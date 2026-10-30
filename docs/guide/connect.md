# 连接设备 {#connect}

插入 Leader Arm 后，SDK 按 USB 标识（VID `0483` / PID `5740`）自动发现串口。多台设备同时插入时，自动发现使用**第一个**匹配端口；请传入端口名以指定设备。指定的端口只要系统已枚举就会打开（即使标识不完全匹配）。

```python
from leapgence.leader_arm import ArmDevice, list_serial_ports

print(list_serial_ports())
```

=== "自动发现"

    ```python
    with ArmDevice() as arm:
        print(arm.port, arm.info().version)
    ```

=== "Windows"

    ```python
    with ArmDevice("COM7") as arm:
        print(arm.port, arm.info().version)
    ```

=== "Linux"

    ```python
    with ArmDevice("/dev/ttyACM0") as arm:
        print(arm.port, arm.info().version)
    ```

=== "macOS"

    ```python
    with ArmDevice("/dev/cu.usbmodem1101") as arm:
        print(arm.port, arm.info().version)
    ```

`ArmDevice` 支持上下文管理器：进入时打开串口，离开时关闭。也可以手动调用 `open()` / `close()`。

```python
arm = ArmDevice()
arm.open()
try:
    print(arm.connected, arm.port)
finally:
    arm.close()
```

找不到设备或打开失败时，会抛出 [`ArmSdkError`](../api.md#exceptions) 的子类。常见处理见 [故障排除](../troubleshooting.md)。
