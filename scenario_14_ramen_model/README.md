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

## 地区目录（已从完整 MDB 确认）

[`region_catalog.json`](region_catalog.json) 由 [`extract_region_catalog.py`](extract_region_catalog.py) 从完整 `master.mdb` 可复现生成，证据链如下：

- `text_data category=426`：地区正式名称；
- `text_data category=428`：地区效果的游戏显示模板；
- `text_data category=486`：效果生效时的游戏显示模板；
- `single_mode_14_region_effect`：98 条基础效果；
- `single_mode_14_region_effect_bonus`：180 条点数档位追加值；
- `single_mode_14_region_feeling`：60 条地区/阶段/拉面诀窍数量；
- `single_mode_14_region_select`：三个地区选择阶段（回合 3、24、48）。

正式名称映射：

| Region ID | 阶段 | 地区 |
|---:|---:|---|
| 1 / 11 | 1 / 3 | 札幌 |
| 2 / 12 | 1 / 3 | 函館 |
| 3 / 13 | 1 / 3 | 新潟 |
| 4 / 14 | 1 / 3 | 福島 |
| 5 / 15 | 1 / 3 | 東京 |
| 6 / 16 | 2 / 3 | 中山 |
| 7 / 17 | 2 / 3 | 中京 |
| 8 / 18 | 2 / 3 | 京都 |
| 9 / 19 | 2 / 3 | 阪神 |
| 10 / 20 | 2 / 3 | 小倉 |

第三阶段的 Region ID 11～20 **只重复地区名称，不重复前两阶段效果**；它们使用独立的 `31xx/32xx` 效果组、基础值和点数档位。

`effect_value` 和点数档位的 `add_value` 在目录中分开保留。UI/模型必须先按地区、`effect_type` 和当前点数选择档位，再按游戏显示模板解释；不得把所有 ActiveEffect 数值统一拼成百分比。


## 拉面资源经济目录

[`resource_economy.json`](resource_economy.json) 是供决策端消费的稳定结构，使用 [`extract_resource_economy.py`](extract_resource_economy.py) 从完整 MDB 生成：

- 三种普通资源：麺のコツ、スープのコツ、トッピングのコツ；三者共享库存上限 10，但各有独立习得 Gauge；
- 万能资源：隠し味の秘訣，独立上限 4，每碗最多替代 2 个普通资源，年底不清空；
- 20 个独立 Region ID 的配方（每碗合计消耗 5 个资源单位）；
- 万能资源固定发放回合；
- 5 张友人卡、5 个外出步骤的万能资源奖励；
- 12 月后半结束后普通资源清空、剩余量转体力的规则边界；
- 防止“只为避免万能溢出而吃面后外出”的决策约束。

目录刻意不伪造尚未证实的 Gauge 增长公式、年底体力换算公式及同回合事件先后顺序。


## 普通诀窍 Gauge 获取目录

[`acquisition_gauge_catalog.json`](acquisition_gauge_catalog.json) 保存已由严格运行时样本与 IL2CPP 命名接口确认的边界：

- 三种诀窍独立计 Gauge；阈值为 7，满 Gauge 获得对应普通诀窍 1 个并重置，超出进度不结转；
- 普通诀窍共享 10 槽 FIFO，库存满时新诀窍仍入库并顶掉最旧诀窍，不是停止获取；
- `FeelingTurnInfoArray` 表示当前三种 Gauge 状态，`CommandFeelingInfoArray` 给出当前训练指令到诀窍类型的映射；
- `FeelingReduceTurnInfoArray[].FeelingTurnArray` 是各指令最终 Gauge 向量，规划端应直接消费最终向量，不从尚未证实的自然增长、地区、合宿、场上角色或卡组公式重建；
- 严格样本仅确认基础向量 `(3,3,4)`、速度训练向量 `(5,3,4)` 以及该样本中关联诀窍 `+2`；这不是通用公式；
- 比赛也会推进 Gauge，但比赛结果依赖仍未测定；不得复用其他剧本的 `heroes_gauge`。


## 吃面动作效果目录

[`ramen_action_catalog.json`](ramen_action_catalog.json) 将“吃面后当前回合效果”与 RMJ 检查点结算奖励严格分开。它由 `single_mode_14_basic_effect`、`single_mode_14_check_point_pt`、`text_data category=427` 和教程文本生成：

- 第一阶段：训练效果 +15%、失败率下降 30%、羁绊 +10；
- 第二阶段：训练效果 +15%、友情 +30%、失败率下降 50%、属性/技能 Pt 单次上限 +20；
- 第三阶段：训练效果 +15%、友情 +45%、失败率下降 100%、属性/技能 Pt 单次上限 +40，以及 Hint 全触发相关效果；
- 三阶段基础盛况 Pt 分别为 300、400、500；
- 效果只持续吃面后的当前回合。

目录保留全部原始条件字段，不臆测吃面基础效果与地区效果是加算还是乘算。


## RMJ 检查点目录

[`checkpoint_catalog.json`](checkpoint_catalog.json) 独立保存 RMJ 检查点与结算原始数据：

- 内部回合 24：成功线 1500，仅有 `result_state=1/2`；
- 内部回合 48：成功线 3000，仅有 `result_state=1/2`；
- 内部回合 72：成功线 3500、大成功线 5000，有 `result_state=1/2/3`；
- 21 条检查点结算效果按阶段和结果状态保存；
- 33 条盛况 Pt 档位被动效果单独保存，不与结算奖励混合。

结算 `effect_type=4/13/14` 的中文语义尚未取得独立文本/调用证据，因此目录只保留原始值，不跨表猜测。
