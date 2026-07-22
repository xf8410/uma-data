# 通用支援卡模拟目录

本目录把完整 `master.mdb` 支援卡表转换为与剧本无关的标准目录，供 Scenario 14、Scenario 8 和旧剧本模拟器复用。

## 生成

```bash
python support_card_model/extract_support_card_catalog.py master.mdb \
  -o support_card_model/support_card_catalog.json
```

输入表：

- `support_card_data`
- `support_card_effect_table`
- `support_card_unique_effect`
- `support_card_limit`
- `text_data`（category 75/76/77/151）

## 输出边界

- 覆盖全部 541 张支援卡；
- 保存 0～4 突对应的等级上限及已生效普通效果；
- 保存效果发生变化的等级断点；
- 普通效果 type 1～32 使用 MDB `text_data category=151` 名称和稳定键；
- 固有效果始终保留完整原始字段；其中 MDB 的 `lv` 暂标为 `lv_raw`，不在缺少独立证据时猜成解锁等级；
- 直接固有 type 1～32 标出 `effect_key`；
- 复杂固有 type 101～122 已解析为机器可读的条件、公式或状态动作，并提供 `evaluate_decoded()` 供模拟器调用；
- 解析依据为 MDB `text_data category=155` 官方描述，并与 `mee1080/umasim@54f3952f8d3a4b14d79ddb3025bce802902295cb` 实现交叉核对；
- type 107 的参考实现自身标注数据解释 TODO，因此只输出 `candidate_formula`，不会冒充已确认。

目录本身只描述卡片效果，不包含任何特定剧本 Link、菜谱、地区或场景倍率。剧本模拟器应在其自身模块中叠加剧本规则。
