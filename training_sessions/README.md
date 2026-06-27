# Training Sessions

育成对局数据，按剧本分目录存储，每局一个JSON文件。

## 目录结构

```
training_sessions/
├── URA/           # URAファイナルズ
├── Aoharu/        # 青春杯（アオハル杯）
├── Climax/        # 巅峰杯（クライマックス）
├── GrandDrive/    # 偶像杯（グランドライブ）
├── GrandMasters/  # 女神杯（グランドマスターズ）
├── LArc/          # 凯旋门杯（プロジェクトL'Arc）
├── UAF/           # UAF运动会
├── Harvest/       # 种田杯（大豊食祭）
├── Mecha/         # 赛博杯（メカウマ娘）
├── Legends/       # 传奇杯（The Twinkle Legends）
├── DesertIsland/  # 无人岛杯
├── HotSpring/     # 温泉杯（ゆこま温泉郷）
└── Dreams/        # 育马者杯（Beyond Dreams）
```

## 文件命名

`{session_id}.json` — 8位随机ID

## 数据格式

```json
{
  "session_id": "a1b2c3d4",
  "scenario": "URA",
  "turn_count": 24,
  "timestamp": 1751097600000,
  "turns": [
    {
      "turn": 1,
      "month": 6,
      "half": 1,
      "stats": {
        "speed": 76, "stamina": 60, "power": 50,
        "guts": 30, "wisdom": 30,
        "skill_pt": 120, "vital": 80, "max_vital": 100,
        "motivation": 4, "has_bad_condition": false
      },
      "trainings": [
        {
          "name": "speed", "is_enable": true,
          "gains": {"Speed":12, "Stamina":0, "Power":2, "Guts":0, "Wisdom":0, "SkillPt":5, "HP":-20},
          "failure_rate": 3, "shining": 1, "heads": 3
        }
      ],
      "action_taken": "Speed",
      "ai_recommend": {"best": "Speed", "score": 7200}
    }
  ],
  "final_stats": {
    "speed": 800, "stamina": 600, "power": 500,
    "guts": 300, "wisdom": 400,
    "total": 2600, "skill_pt": 45
  }
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `turn` | int | 回合数 (month-1)*2+half |
| `action_taken` | string | 玩家实际选择: Speed/Stamina/Power/Guts/Wisdom/Rest/Outing/Unknown |
| `motivation` | int | 干劲 1=絶不調~5=絶好調 |
| `shining` | int | 彩圈人数 |
| `heads` | int | 训练伙伴人数 |
| `has_bad_condition` | bool | 是否有debuff(病気等) |

## 用途

用于训练MCTS+NN决策模型：
- **State**: stats + trainings → 输入特征向量
- **Policy**: action_taken → 监督学习标签
- **Value**: final_stats.total → 回报信号

不同剧本的属性上限和训练偏好不同，分目录存储确保训练数据不混淆。
