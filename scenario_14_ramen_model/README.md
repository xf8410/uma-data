# 拉面杯模型（Scenario 14，边界已建立）

> **状态：尚未建立可训练或可用于 App 推理的模型。** 本目录先用于隔离拉面杯证据，防止误用 Scenario 8 的 Cook/种田杯规则。

## 数据范围

只将以下数据视为 Scenario 14 的直接候选输入：

- Master 表：`single_mode_14_*`
- 运行时类：`WorkSingleModeScenarioRamen*`
- 运行时状态：`Region`、`Feeling`、`CommandInfo`、`CheckPoint`、`ActiveEffect`、`UrafEffect`、`LastTastingInfo`
- 经独立验证的通用育成状态和训练 CommandId

## 明确排除

以下表属于 Scenario 8 Cook / 豊食祭 / 种田杯，不得复制进拉面杯模型：

- `single_mode_cook_dish*`
- `single_mode_cook_garden*`
- `single_mode_cook_material*`
- `single_mode_cook_coin*`
- `single_mode_cook_success*`
- `single_mode_cook_cooking*`
- `single_mode_cook_power_data`

对应模型位于 [`../scenario_08_cook_model/`](../scenario_08_cook_model/)。

## 接入前必须确认

1. `ActiveEffect.EffectCategory + EffectId` 与具体 `single_mode_14_*_effect` 表记录的关联。
2. `effect_type`、`effect_value` 与各 `condition_type_n/value_n` 的实际语义和单位。
3. `FeelingInfoArray`、`CommandFeelingInfoArray`、持续回合与训练指令之间的关系。
4. `CheckPointPt`、成功/大成功阈值及 `result_state` 的运行时行为。
5. 普通训练、拉面指令、`RecommendType` 和 `base_command_id` 是否使用同一枚举。

未知字段必须保留原始 ID、数值和来源，不能先猜成百分比或属性名称。
