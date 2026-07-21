# 剧本模型数据边界

为避免把两个料理主题剧本混为一谈，本仓库按游戏剧本 ID 隔离模型和解释层数据。

| 剧本 | 目录 | 专属 Master 表/运行时类 |
|---|---|---|
| Scenario 8 — Cook / 豊食祭 / 种田杯 | `scenario_08_cook_model/` | `single_mode_cook_*`、`WorkSingleModeScenarioCook*` |
| Scenario 14 — Ramen / トレセン軒 / 拉面杯 | `scenario_14_ramen_model/` | `single_mode_14_*`、`WorkSingleModeScenarioRamen*` |

## 强制边界

1. `single_mode_cook_dish*`、`single_mode_cook_garden*`、`single_mode_cook_material*`、`single_mode_cook_coin*`、`single_mode_cook_success*` 和 `single_mode_cook_power_data` 只进入 Scenario 8 模型。
2. Scenario 14 优先使用 `single_mode_14_*`，并与运行时 `Region`、`Feeling`、`CommandInfo`、`CheckPoint`、`ActiveEffect`、`UrafEffect` 数据交叉验证。
3. 相同的 `effect_type` 数字不得跨来源表直接复用语义；解释时必须保留来源表、条件字段和原始值。
4. 未经运行时或调用逻辑验证，不把 `EffectValue` 自动显示为百分比，也不把奖励预览当作实际抽选结果。
5. 公共 Master JSON 可继续保留在仓库根目录，但模型快照、规则、测试和产物必须放入对应剧本目录。
