# UMA AI Data

赛马娘AI助手静态数据仓库，供App远程加载 + IL2CPP运行时探查数据。

> **2026-07-23 更新**
> - `support_card_model/`：支援卡模型 v2（573 固有槽证据分级解码，43 测试）
> - `scenario_14_ramen_model/`：拉面杯剧本模型与模拟器（接受插件 `/summary` 真实 schema，`ramen.checkpoint_pt` 与旧 `check_point_pt` 双写法兼容）
> - `exports/`：19 个体积数据导出（MDB 全量导出、IL2CPP 类分类、相性/因子/事件等，共 211MB，**Git LFS 存储**，克隆需 `git lfs pull`；SHA256 基线见 `exports/SHA256SUMS.txt`，由 exports_lfs_check workflow 校验）

## 数据文件

| 文件 | 记录数 | 大小 | 说明 |
|------|--------|------|------|
| uma_names.json | 813 | 53KB | 角色名称映射（日文名→中文昵称） |
| uma_events.json | 8063 | 1.8MB | 育成事件（含选项和效果） |
| uma_skills.json | 2008 | 179KB | 技能数据 |
| uma_factors.json | 2436 | 256KB | 因子效果 |
| card_db.json | 541 | 399KB | 全量支援卡数据（lv50重建） |
| support_card_effect_table.json | 541×5 | 939KB | 效果表（lv1/10/20/25/30/35/40/45/50） |
| support_card_unique_effect.json | 399 | 82KB | 独特效果 |

## 使用方式

直接用 raw.githubusercontent.com 的URL加载：

```
https://raw.githubusercontent.com/xf8410/uma-data/main/uma_names.json
```

App端用 OkHttp 或 HttpURLConnection 下载，缓存到本地。

---

## IL2CPP 运行时探查数据

通过 SO 插件 v3.22.79+ 的 IL2CPP 端点从游戏进程内实时读取。

### SO 插件端点列表（v3.22.79）

| 端点 | 说明 |
|------|------|
| `/il2cpp/dump?name=X` | dump单例实例的字段值 |
| `/il2cpp/call?name=X&method=M` | runtime_invoke调用方法 |
| `/il2cpp/tree?name=X&depth=N` | 类继承树（depth>3可能闪退） |
| `/il2cpp/field?name=X` | 读取类的字段定义 |
| `/il2cpp/classes?keyword=X` | 按关键词搜索类名 |
| `/il2cpp/static?name=X` | 读取静态类的字段值 |
| `/il2cpp/search_float?value=X` | 在代码段搜索浮点常量 |

HTTP端口：**18765**

### 已确认的枚举值

#### Motivation（やる気等级）
| 值 | 名称 | 含义 |
|----|------|------|
| 0 | Random | 特殊值（初始化用） |
| 1 | Min | 最差 |
| 2 | Low | 低 |
| 3 | Middle | 普通 |
| 4 | High | 高 |
| 5 | Max | 最好 |

#### GainParameterType（增益参数类型）
| 值 | 名称 | 含义 |
|----|------|------|
| 0 | Speed | 速度 |
| 1 | Stamina | 耐力 |
| 2 | Power | 力量 |
| 3 | Guts | 根性 |
| 4 | Wiz | 智力 |
| 5 | Hp | 体力 |
| 6 | MaxHp | 最大体力 |
| 7 | **Motivation** | **やる気** |
| 8 | SkillPoint | 技能点 |
| 9 | Fan | 粉丝数 |
| 10 | MaxSpeed | 最大速度 |
| 11 | MaxStamina | 最大耐力 |
| 12 | MaxPower | 最大力量 |
| 13 | MaxGuts | 最大根性 |
| 14 | MaxWiz | 最大智力 |

#### ParamUpType（属性增长类型）
| 值 | 名称 | 含义 |
|----|------|------|
| 0 | Normal | 正常增长 |
| 1 | OverDefaultMax | 超过默认上限的增长（对应 TRAINING_PARAMETER_GAIN_RATE_FOR_OVER_MAX_DEFAULT=0.5） |

#### TrainingResultType（训练结果）
| 值 | 名称 | 含义 |
|----|------|------|
| 0 | GreatSuccess | 大成功 |
| 1 | Success | 成功 |
| 2 | Failure | 失败 |

### SingleModeDefine 常量（v3.22.79 实测确认）

| 字段 | 值 | 含义 |
|------|-----|------|
| MAX_PARAMETER_BASELINE | 1200 | 属性上限基准 |
| RANK_U_MAX_PARAMETER | 2000 | U段上限 |
| VITAL_DEFAULT_MAX | 100 | 默认体力上限 |
| VITAL_VALUE_MAX | 120 | 体力值上限 |
| EQUIP_SUPPORT_CARD_MAX | 5 | 支援卡上限 |
| SUPPORT_CARD_WITH_FRIEND_MAX | 6 | 含友人支援卡上限 |
| TAZUNA_SCALE | 0.8 | 绳桥缩放 |
| CUT_PLAY_SPEED_1X | 1.0 | 倍速1x |
| CUT_PLAY_SPEED_3X | 3.0 | 倍速3x |
| CUT_PLAY_DURATION_3X | 0.5 | 3x播放时长 |
| SUCCESS_SE_VALUE_MAX | 0.6 | 成功SE最大值 |
| TRAINING_PARAMETER_GAIN_RATE_FOR_OVER_MAX_DEFAULT | 0.5 | 超上限训练增益率 |
| STATUS_UP_VALUE_MAX | 100 | 单次属性增长上限 |
| CHARA_EFFECT_SKILL_DISCOUNT_RATE | 10 | 角色效果技能折扣率 |
| NO_WIN_GAMEOVER_TURN | 41 | 无胜场失败回合 |

### 心情系数调查状态

- **search_float** 对 0.6/0.75/0.8/0.9/1.0/1.1/1.2 和 0.1 全部 0 命中 → 系数不是硬编码浮点数
- **SingleModeDefine** 41个常量中确认无 motivation/yaruki 相关 → 不是静态常量
- **Motivation枚举** 已确认等级名(Min/Low/Middle/High/Max)，但**系数值（0.8/0.9/1.0/1.1/1.2）未找到**
- 推测：系数可能存在mdb数据表中，或用整数算术运算

### 关键运行时偏移

| 对象 | 偏移/地址 | 说明 |
|------|-----------|------|
| WorkDataManager 单例 | 0x740271f960 | 78字段，含训练数据 |
| umamusume.dll 代码段 | base=0x7008e49000, size=2682880 | search_float搜索范围 |
| SingleModeDefine | instance=null | 41个静态字段，全部读取成功 |

### 探查会话记录

| 目录 | 日期 | 内容 |
|------|------|------|
| il2cpp_probe/20260706/ | 7月6日 | 初次IL2CPP探查 |
| il2cpp_probe/20260707/ | 7月7日 | search_float、WorkDataManager dump |
| il2cpp_probe/20260707_session2/ | 7月7日 | GainParameterType enum、SingleModeDefine完整数据、TrainingCommand搜索 |

### 类搜索汇总（やる気/训练计算相关）

| 关键词 | 命中 | 关键类 |
|--------|------|--------|
| Motivation | 38 | **Motivation(enum,9字段)**, MotivationDisp(11), MotivationChangedInfoByBuff(2) |
| Feeling | 92 | 全部拉面场景专用 |
| TrainingResult | 6 | TrainingResultType(enum) |
| ParamUp | 15 | ParamUpType(enum), ParamUpTypeA2UContext(8) |
| SingleModeGain | 7 | ObscuredSingleModeGainParameterInfo(2), SingleModeGainPartnerSupportEffectInfo(12) |
| ChangeParameter | 29 | **WorkSingleModeChangeParameterInfo(75字段)**, ChangeParameterInfo(11) |
| TrainingCommand | 32 | SingleModeEffectedTrainingCommandInfo(12), SingleModeTrainingCommandService(0,纯逻辑) |
| TrainingCalc/GainCalc/ParameterCalc | 0 | 计算层类名不含这些关键词 |
| TrainingGain | 8 | TrainingGainParameterEntity(2) |
