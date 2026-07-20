# 种田杯模型（重建中）

> **状态：不可用于 App 推理。** 2026-07-20 上传的模型及生成管线已确认被错误标签污染，现已删除。

## 固定配置

- 剧本：种田杯 / Cook / Harvest，`scenario_id = 8`
- 育成对象：原皮五星草上飞，`card_id = 101101`
- 初始五维：`[118, 91, 129, 96, 116]`
- 成长率：`[20, 0, 10, 0, 0]`
- 目标赛回合：`[11, 22, 33, 45, 47, 59, 66, 71]`

草上飞基础数据和目标赛程来自 `xulai1001/UmaSimulator` 的 `cook` 分支；种田杯机制和训练协议以 `hzyhhzy/UmaAi` 的 `Cook2` 分支为对照。

## 删除的污染产物

- `cook_model.onnx`：引用未上传的外部权重，无法单文件加载。
- `cook_model.pt`、`cook_model_state_dict.pt`：由错误轨迹和错误标签训练。
- `train_cook_v2.py`、`cook_game.py`：回合推进、动作标签、value、评估和角色建模均存在决定性错误。
- `cook_static_data.json`：生成说明把 `scenario_id=14`（拉面杯）误标为种田杯。
- `cardDB.json`、`umaDB.json`：大体积全量副本未被模型正确使用；重建只保留可追溯的固定配置。

新模型只有在完整育成轨迹、比赛回合、随机事件、角色事件、独立验证集、单文件 ONNX 和 PyTorch/ONNX 一致性全部通过后才会发布。
