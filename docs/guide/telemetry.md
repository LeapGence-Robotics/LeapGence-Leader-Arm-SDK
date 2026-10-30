# 遥测与按键 {#telemetry}

每帧遥测包含 7 个角度（度）和 2 个按键状态。`angles` 顺序固定为：

| 下标 | 含义 |
|---|---|
| `0` | Joint 1 |
| `1` | Joint 2 |
| `2` | Joint 3 |
| `3` | Joint 4 |
| `4` | Joint 5 |
| `5` | Joint 6 |
| `6` | 夹爪（gripper）角度 |

`HomeOffsets.offsets` 与 `AxisCalib.signs` 使用同一顺序。

## 迭代读取 {#iterate}

```python
from leapgence.leader_arm import ArmDevice

with ArmDevice() as arm:
    for sample in arm.telemetry(timeout=2):
        print(sample.angles, sample.keys)
```

`timeout` 是**等待下一帧到达**的秒数，不是采样周期。设备会持续推送遥测；超时只表示在这段时间内没有新帧，并抛出 `DeviceTimeoutError`。省略 `timeout` 时会一直等到下一帧。

`Telemetry` 字段：

| 字段 | 含义 |
|---|---|
| `angles` | 7 个角度（度）：Joint 1–6，最后一项为夹爪 |
| `keys` | 2 个整数按键状态 |
| `timestamp` | 本机收到该帧的时间，**毫秒**（`time.time() * 1000`） |
| `health` | 可选；多数帧为 `None`，仅在设备同时发来健康包时附带 |

`sample.to_dict()` 的键为 `angles`、`keys`、`t`（即 `timestamp`），若有健康信息则还有 `health`。

## 后台回调 {#callbacks}

需要在自己的主循环里继续干活时，用 `on_telemetry` 在后台接收：

```python
def on_sample(sample):
    print(sample.angles, sample.keys)

unsubscribe = arm.on_telemetry(on_sample)
# ... 你的主循环 ...
unsubscribe()
```

`on_health` 在收到健康包时回调，参数为 `DeviceHealth`。`on_disconnect` 仅在**意外断开**时回调（正常 `close()` 不会触发），参数为 `Exception` 或 `None`。

各回调的返回值是取消函数，调用后停止接收。
