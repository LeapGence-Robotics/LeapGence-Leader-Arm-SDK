# 示例 {#examples}

仓库里的 `examples/` 可直接运行（无需先安装，脚本会把 `src/` 加入路径）。

| 文件 | 作用 |
|---|---|
| `examples/joint_demo.py` | 核心 SDK：发现 → 连接 → 读状态 → 关节遥测 / 力反馈 |
| `examples/ee_pose_demo.py` | 末端位姿：遥测 + NumPy FK（需 numpy 与 `description/leader_arm_{left,right}`） |
| `examples/urdf_fk.py` | EE demo 用的 NumPy FK 辅助模块（非 SDK API） |
| `examples/monitor.py` | 持续打印关节数据 |

## 关节 demo

```bash
python examples/joint_demo.py
python examples/joint_demo.py --port COM7 --samples 20 --force 32
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--port` | 自动发现 | 例如 `COM7` / `/dev/ttyACM0` |
| `--samples` | `10` | 遥测帧数 |
| `--force` | `0` | 力反馈振动强度 0–255（0 关闭） |
| `--timeout` | `2.0` | 等待下一帧的秒数 |

## 末端位姿 demo

```bash
python examples/ee_pose_demo.py
python examples/ee_pose_demo.py --side left --samples 20
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `--port` | 自动发现 | 串口 |
| `--samples` | `10` | 帧数 |
| `--timeout` | `2.0` | 等待下一帧的秒数 |
| `--side` | 读设备 | `left` / `right`；默认 `get_axis_calib().side` |
| `--urdf` | — | 自定义 URDF（覆盖 `--side`）；默认 `description/leader_arm_{side}/urdf/leader_arm_{side}.urdf` |

假设遥测零位与 URDF 零位一致；输出为 `link6` 在 `base_link` 下的 `xyz`（m）与 `rpy`（度）。

机器人描述位于 `description/leader_arm_left` 与 `description/leader_arm_right`。

## 持续监视

```bash
python examples/monitor.py
```
