# LeapGence Leader Arm

USB 连接主臂后，即可读取 Joint 1–6 与夹爪角度、按键，下发力反馈，并完成回零与校准。

适用于 Windows、Linux、macOS，需要 Python 3.10 或更高版本。

```python
from leapgence.leader_arm import ArmDevice

with ArmDevice() as arm:
    print(arm.info().version)
    sample = next(arm.telemetry(timeout=2))
    print(sample.angles, sample.keys)
```

<div class="grid cards" markdown>

-   :material-download: **[开始使用](getting-started.md)**

    ---

    安装 SDK，配置 Linux 权限，完成第一次连接

-   :material-usb: **[连接设备](guide/connect.md)**

    ---

    按 USB 标识自动发现串口，或指定 COM / ttyACM

-   :material-axis-arrow: **[遥测与按键](guide/telemetry.md)**

    ---

    读取 Joint 1–6、夹爪角度和 2 个按键状态

-   :material-code-braces: **[API 参考](api.md)**

    ---

    `ArmDevice`、数据模型与异常类型

</div>

[开始使用](getting-started.md){ .md-button .md-button--primary }
[查看 API](api.md){ .md-button }
