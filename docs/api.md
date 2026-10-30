# API 参考 {#api}

主入口：

```python
from leapgence.leader_arm import ArmDevice, list_serial_ports
```

## ArmDevice

线程安全的同步接口。建议用 `with ArmDevice() as arm:` 管理生命周期。

| 成员 | 说明 |
|---|---|
| `ArmDevice(port=None)` | 创建实例；`port` 可省略，打开时自动发现（取第一个匹配口） |
| `open(port=None)` | 打开串口，返回实际端口名 |
| `close()` | 关闭串口并停止后台线程 |
| `connected` | 是否已连接 |
| `port` | 当前端口 |
| `info(timeout=3.0, *, attempts=3)` | 读取固件版本，返回 `FwInfo`（默认最多试 3 次） |
| `probe(timeout=0.8)` | 单次 INFO（`info(..., attempts=1)`），用于快速确认端口是否为 Leader Arm |
| `telemetry(timeout=None)` | 迭代 `Telemetry`；`timeout` 为等待下一帧的秒数，超时抛 `DeviceTimeoutError` |
| `on_telemetry(callback)` | 后台遥测回调，返回取消函数 |
| `on_health(callback)` | 收到健康包时回调 `DeviceHealth`，返回取消函数 |
| `on_disconnect(callback)` | 意外断开时回调（参数为异常或 `None`；正常 `close()` 不触发），返回取消函数 |
| `set_force(force)` | 力反馈（振动强度），夹到 0–255（0 关闭，255 最强）后排队下发，不阻塞；返回实际整数值 |
| `set_home()` / `get_home()` / `clear_home()` | Home 偏移（度，与 `angles` 同序）；出厂通常已设好，仅在需要时再 `set_home` / `clear_home` |
| `get_axis_calib()` | 读取轴校准（固件 ≥ v1.0.2） |

## 发现串口 {#discovery}

| 函数 | 说明 |
|---|---|
| `list_serial_ports()` | 列出当前串口，返回 `PortInfo` 列表 |
| `find_port(prefer=None)` | 指定端口名则打开该口；否则按 VID/PID 取第一个 Leader Arm |

找不到匹配端口时抛出 `PortNotFoundError`。

## 数据模型 {#models}

均为不可变 dataclass，多数提供 `to_dict()`。

| 类型 | 主要字段 |
|---|---|
| `Telemetry` | `angles`（Joint 1–6 + 夹爪，度）、`keys`（2 个整数）、`timestamp`（本机收包时间，毫秒）、`health`（常为 `None`） |
| `DeviceHealth` | 设备上报的健康快照：`expected`、`live`、`arm_node`、`online`、`enc_ok` |
| `FwInfo` | `major` / `minor` / `patch`、`version`（如 `"1.0.2"`） |
| `HomeOffsets` | `offsets`（度，与 `angles` 同序：Joint 1–6 + 夹爪） |
| `AxisCalib` | `signs`（同序）、`trigger_signed`、`trigger_travel`、`side` |
| `PortInfo` | `device`、`description`、`vid`、`pid` |

## 异常 {#exceptions}

均继承 `ArmSdkError`，可按类型捕获。

| 类型 | 场景 |
|---|---|
| `ArmSdkError` | 所有预期失败的基类 |
| `PortNotFoundError` | 未找到匹配串口 |
| `TransportError` | 串口打开、读写或断开失败 |
| `DeviceTimeoutError` | 命令或遥测超时 |
| `ProtocolError` | 帧格式异常 |
| `DeviceRejectedError` | 设备返回 NAK |
