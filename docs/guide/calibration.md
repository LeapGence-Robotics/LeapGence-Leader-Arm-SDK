# 回零与校准 {#calibration}

## Home 偏移 {#home}

设备出厂通常已设好 Home。仅在需要重新定义零位时再调用 `set_home()`；日常用 `get_home()` 读取即可。`clear_home()` 会清除已保存偏移，请谨慎使用。

```python
print(arm.get_home())
# arm.set_home()    # 仅在需要重新设零时使用
# arm.clear_home()  # 会清除已保存偏移
```

`HomeOffsets.offsets` 单位为度，与遥测 `angles` 同序：Joint 1–6，最后一项为夹爪。

## 轴校准 {#axis}

极性、扳机行程和左右臂保存在设备中，可用 `get_axis_calib()` 读取。需要固件 **v1.0.2** 或更高版本：

```python
print(arm.get_axis_calib())
```

| 字段 | 含义 |
|---|---|
| `signs` | 7 个极性（Joint 1–6 + 夹爪），每个为 `1` 或 `-1` |
| `trigger_signed` | 扳机是否使用有符号行程 |
| `trigger_travel` | 扳机行程（度） |
| `side` | `"left"` 或 `"right"` |

固件过旧时，读取会失败。处理方式见 [故障排除](../troubleshooting.md)。
