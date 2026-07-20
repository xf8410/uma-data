# 种田杯（料理杯/Harvest）AI 模型

## 文件说明
| 文件 | 说明 | 大小 |
|------|------|------|
| cook_model.onnx | ONNX模型（juece推理用） | 12KB |
| cook_model.pt | PyTorch JIT模型（traced） | 790KB |
| cook_model_state_dict.pt | PyTorch state_dict | 790KB |
| cook_game.py | 种田杯模拟器（移植自UmaAi Cook2） | 25KB |
| train_cook_v2.py | 训练脚本 | 15KB |
| cook_static_data.json | MDB静态数据（技能/卡片/种田杯表） | 177KB |
| cardDB.json | 支援卡数据（371张，来自UmaAi） | 1.1MB |
| umaDB.json | 角色数据（来自UmaAi） | 81KB |

## 模型架构
- 输入: 186维（种田杯状态特征）
- 输出: 56维 = 53 policy + 3 value
- 隐藏层: 256维, 3层MLP
- 激活: ReLU

## 训练过程
1. Phase 1: 2000局随机自对弈 → 156K样本
2. Phase 2: 20 epochs训练
3. Phase 3: 评估 → avg=1256
4. Phase 4: 1000局模型引导自对弈 → 78K样本
5. Phase 5: 25 epochs二次训练
6. Phase 6: 最终评估 → avg=1339, max=2036

## 数据来源
- 模拟器: UmaAi Cook2分支 (hzyhhzy/UmaAi)
- 支援卡数据: UmaAi Scripts/export_support_card
- MDB静态数据: master.mdb scenario_id=14
- 技能数据: skill_data + single_mode_skill_need_point

## juece App集成
juece通过HTTP从uma-data仓库下载cook_model.onnx，
用ONNX Runtime推理，输出policy+value。
