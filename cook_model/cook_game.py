"""
赛马娘种田杯（料理杯/Harvest）模拟器 — Python移植版
移植自 UmaAi Cook2 分支 (hzyhhzy/UmaAi)
原始作者: hzyhhzy
移植日期: 2026-07-20

核心机制:
  1. 5种农田种植+升级，每4回合收获
  2. 14种菜品（三明治/咖喱/5种1级/5种2级/G1拼盘）
  3. 料理pt → 训练加成/技能pt/得意率/大成功率
  4. 大成功系统（hint/体力/心情/羁绊/分身/体力上限）
  5. 试食会5次历史
  6. 78回合育成（12回合/年 × 3年 + 42回合URA）
"""

import random
import json
from enum import IntEnum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ============================================================
# 常量
# ============================================================

class TrainActionType(IntEnum):
    speed = 0
    stamina = 1
    power = 2
    guts = 3
    wiz = 4
    rest = 5
    outgoing = 6
    race = 7
    none = -1

class DishType(IntEnum):
    none = 0
    sandwich = 1    # 速+力+智 25%
    curry = 2       # 速+耐+根 25%
    speed1 = 3      # 150+80  60%
    stamina1 = 4
    power1 = 5
    guts1 = 6
    wiz1 = 7
    speed2 = 8      # 250+80  90%~100%
    stamina2 = 9
    power2 = 10
    guts2 = 11
    wiz2 = 12
    g1plate = 13    # 5*80

# 料理等级
DISH_LEVEL = [0,1,1,2,2,2,2,2,3,3,3,3,3,4]

# 料理主训练
DISH_MAIN_TRAINING = [-1,-1,-1,0,1,2,3,4,0,1,2,3,4,-1]

# 料理获得pt
DISH_GAIN_PT = [0,250,250,500,500,500,500,500,800,800,800,800,800,1500]

# 料理原料消耗 [dish][5种菜]
DISH_COST = [
    [0,0,0,0,0],
    [25,0,50,0,50],
    [25,50,0,50,0],
    [150,0,80,0,0],
    [0,150,0,80,0],
    [0,80,150,0,0],
    [40,0,40,150,0],
    [80,0,0,0,150],
    [250,0,80,0,0],
    [0,250,0,80,0],
    [0,80,250,0,0],
    [40,0,40,250,0],
    [80,0,0,0,250],
    [80,80,80,80,80],
]

# 料理对哪些训练有加成
DISH_TRAINING_BONUS_EFFECTIVE = [
    [0,0,0,0,0],
    [1,0,1,0,1],
    [1,1,0,1,0],
    [1,0,0,0,0],
    [0,1,0,0,0],
    [0,0,1,0,0],
    [0,0,0,1,0],
    [0,0,0,0,1],
    [1,0,0,0,0],
    [0,1,0,0,0],
    [0,0,1,0,0],
    [0,0,0,1,0],
    [0,0,0,0,1],
    [1,1,1,1,1],
]

# 农田升级消耗
FARM_LV_COST = [0,100,180,220,250]

# 农田等级收获基础值
HARVEST_BASIC = [0,20,20,30,40,40]

# 农田等级收获追加值
HARVEST_EXTRA = [0,20,30,30,40,40]

# 材料上限
MATERIAL_LIMIT = [0,200,400,600,800,999]

# 料理pt分档加成
DISH_PT_TRAINING_BONUS = [0,10,16,21,25,28,30,30]
DISH_PT_SKILL_PT_BONUS = [0,15,24,33,42,51,60,60]
DISH_PT_DEYILV_BONUS = [0,5,8,11,14,17,20,20]
DISH_PT_BIG_SUCCESS_RATE = [0,15,18,20,22,24,25,100]

# 休息/比赛绿色概率
REST_GREEN_RATE = 0.2
RACE_GREEN_RATE = 0.4

# 大成功buff概率 [料理等级][buff类型]
# buff类型: 1=体力, 2=心情, 3=羁绊, 4=分身, 5=体力上限
BIG_SUCCESS_BUFF_PROB = [
    [0,0,0,0,0,0],
    [0,34,33,33,0,0],
    [0,30,30,0,40,0],
    [0,30,20,0,50,0],
    [0,0,100,0,0,0],
]

BIG_SUCCESS_BUFF_EXTRA_PROB = [
    [0,0,0,0,0,0],
    [0,0,0,0,0,10],
    [0,10,10,30,10,10],
    [0,15,15,0,15,10],
    [0,0,0,0,100,0],
]

# 训练基础值 [训练类型][训练等级0-4][速,耐,力,根,智,pt,体力消耗]
TRAINING_BASIC_VALUE = [
    # 速
    [[11,0,2,0,0,5,-19],[12,0,2,0,0,5,-20],[13,0,2,0,0,5,-21],[14,0,3,0,0,5,-23],[15,0,4,0,0,5,-25]],
    # 耐
    [[0,8,0,5,0,5,-20],[0,9,0,5,0,5,-21],[0,10,0,6,0,5,-22],[0,11,0,7,0,5,-24],[0,12,0,8,0,5,-26]],
    # 力
    [[0,4,9,0,0,5,-20],[0,4,10,0,0,5,-21],[0,4,11,0,0,5,-22],[0,5,12,0,0,5,-24],[0,6,13,0,0,5,-26]],
    # 根
    [[2,0,2,10,0,5,-20],[2,0,2,11,0,5,-21],[2,0,2,12,0,5,-22],[3,0,3,13,0,5,-24],[3,0,3,14,0,5,-26]],
    # 智
    [[2,0,0,0,8,5,5],[2,0,0,0,9,5,5],[2,0,0,0,10,5,5],[3,0,0,0,11,5,5],[4,0,0,0,12,5,5]],
]

# 失败率基础值 [训练类型][训练等级0-4]
FAIL_RATE_BASIC = [
    [520,524,528,532,536],
    [507,511,515,519,523],
    [516,520,524,528,532],
    [532,536,540,544,548],
    [320,321,322,323,324],
]

# 属性上限
FIVE_STATUS_LIMIT = [2300,1000,2200,2200,1500]

# 属性评分表 (0-2800)
FIVE_STATUS_FINAL_SCORE = None  # 后面加载

# 料理pt等级
def dish_pt_level(dish_pt: int) -> int:
    if dish_pt < 300: return 0
    elif dish_pt < 1500: return 1
    elif dish_pt < 2500: return 2
    elif dish_pt < 5000: return 3
    elif dish_pt < 7000: return 4
    elif dish_pt < 10000: return 5
    elif dish_pt < 12000: return 6
    else: return 7

# 总回合数
TOTAL_TURN = 78

# Link角色
LINK_CHARAS = [9002,1001,1028,1030,1051,1104]

def is_link_chara(chara_id: int) -> bool:
    if chara_id > 100000:
        chara_id //= 100
    return chara_id in LINK_CHARAS


# ============================================================
# 游戏状态
# ============================================================

@dataclass
class Person:
    card_id: int = 0
    friendship: int = 0
    is_card: bool = True
    at_train: int = -1  # 当前在哪个训练
    hint_level: int = 0  # hint等级


class CookGame:
    """种田杯完整模拟器"""

    def __init__(self, rand: random.Random = None):
        self.rand = rand or random.Random()

        # 基本状态
        self.turn = 0
        self.five_status = [0, 0, 0, 0, 0]  # 速耐力根智
        self.skill_point = 0
        self.vital = 100
        self.max_vital = 100
        self.motivation = 3  # 干劲 1-5
        self.chara_id = 0
        self.chara_stars = 3

        # 种马因子
        self.zhongma_blue_count = [0, 0, 0, 0, 0]
        self.zhongma_extra_bonus = [0, 0, 0, 0, 0, 0]

        # 训练等级
        self.train_level = [1, 1, 1, 1, 1]  # 5个训练的等级
        self.train_level_count = [0, 0, 0, 0, 0]  # 升级进度

        # 人头
        self.persons: List[Person] = [Person() for _ in range(6)]
        self.person_distribution = [[-1]*5 for _ in range(5)]  # [训练][人头]
        self.friendship_noncard_yayoi = 0
        self.friendship_noncard_reporter = 0

        # 友人卡
        self.friend_type = 0  # 0=无, 1=凉花, 2=理事长
        self.friend_is_ssr = True
        self.friend_person_id = -1

        # 种田杯专属状态
        self.cook_material = [0, 0, 0, 0, 0]  # 五种菜个数
        self.cook_dish_pt = 0  # 料理pt
        self.cook_dish_pt_turn_begin = 0  # 回合开始时的料理pt
        self.cook_farm_level = [1, 1, 1, 1, 1]  # 五种农田等级
        self.cook_farm_pt = 0  # 农田升级pt
        self.cook_dish_sure_success = False  # 大成功确定
        self.cook_dish = 0  # 当前生效的菜 (DishType)
        self.cook_win_history = [0, 0, 0, 0, 0]  # 5次试食会结果 0=普通 1=大满足 2=超满足

        # 收获历史 (4回合循环)
        self.cook_harvest_history = [-1, -1, -1, -1]  # 4回合分别是哪4种菜
        self.cook_harvest_green_history = [False, False, False, False]  # 是否绿圈
        self.cook_harvest_extra = [0, 0, 0, 0, 0]  # 每回合人头附加菜量

        # 训练获得的菜
        self.cook_train_material_type = [0]*8  # 训练获得的菜种类
        self.cook_train_green = [False]*8  # 是否绿圈
        self.cook_main_race_material_type = 0  # 比赛回合的菜种类

        # 料理pt等级效果
        self.cook_dishpt_success_rate = 0  # 大成功率
        self.cook_dishpt_training_bonus = 0  # 训练加成
        self.cook_dishpt_skillpt_bonus = 0  # 技能pt加成
        self.cook_dishpt_deyilv_bonus = 0  # 得意率加成

        # 状态
        self.is_racing = False
        self.is_qie_zhe = False
        self.is_ai_jiao = False

        # 评分
        self.pt_score_rate = 2.0
        self.hint_pt_rate = 6.5
        self.event_strength = 20

    # ============================================================
    # 核心机制
    # ============================================================

    def is_xiahesu(self) -> bool:
        """是否为夏合宿 (回合36-39, 60-63)"""
        return (36 <= self.turn <= 39) or (60 <= self.turn <= 63)

    def turn_idx_in_harvest_loop(self) -> int:
        """收获周期里的第几回合 (turn%4)，夏合宿恒为0"""
        if self.is_xiahesu():
            return 0
        return self.turn % 4

    def is_dish_legal(self, dish_id: int) -> bool:
        """检查料理是否允许"""
        if self.cook_dish != DishType.none:
            return False

        level = DISH_LEVEL[dish_id]
        if level == 0:
            return False
        elif level == 1:
            pass
        elif level == 2:
            if self.turn < 24:
                return False
        elif level == 3:
            if self.turn < 48:
                return False
        elif level == 4:
            if self.turn < 72:
                return False

        # 检查材料
        for i in range(5):
            cost = DISH_COST[dish_id][i]
            if dish_id == DishType.g1plate:
                if self.cook_win_history[4] < 2:
                    cost = 100
            if self.cook_material[i] < cost:
                return False
        return True

    def max_farm_pt_until_now(self) -> int:
        """假如全程绿圈，最多多少pt"""
        total_cost = 0
        for i in range(5):
            for j in range(1, self.cook_farm_level[i]):
                total_cost += FARM_LV_COST[j]

        turn = self.turn
        if turn <= 39:
            normal_cycle = turn // 4
        elif turn <= 63:
            normal_cycle = turn // 4 - 1
        elif turn <= 72:
            normal_cycle = turn // 4 - 2
        else:
            normal_cycle = 72 // 4 - 2

        if turn <= 36:
            small_cycle = 0
        elif turn <= 39:
            small_cycle = turn - 36
        elif turn <= 60:
            small_cycle = 4
        elif turn <= 63:
            small_cycle = 4 + turn - 60
        elif turn <= 72:
            small_cycle = 8
        else:
            small_cycle = 8 + turn - 72

        max_pt = normal_cycle * 160 + small_cycle * 75
        return max_pt - total_cost

    def calculate_harvest_num(self, is_after_train: bool = True) -> List[int]:
        """计算收获五种菜的数量，以及农田pt数"""
        small_harvest = self.is_xiahesu() or self.turn >= 72
        harvest_turn_num = 1 if small_harvest else 4

        if not is_after_train:
            harvest_turn_num = 0 if small_harvest else self.turn % 4

        harvest = [0]*5
        for i in range(5):
            harvest[i] = HARVEST_BASIC[self.cook_farm_level[i]]
            if small_harvest:
                harvest[i] //= 2
            harvest[i] += self.cook_harvest_extra[i]

        green_num = 0
        for i in range(harvest_turn_num):
            mat_type = self.cook_harvest_history[i]
            if mat_type == -1:
                continue  # 未选择的回合跳过
            harvest[mat_type] += HARVEST_EXTRA[self.cook_farm_level[mat_type]]
            if self.cook_harvest_green_history[i]:
                green_num += 1

        # 绿圈倍率
        if small_harvest:
            multiplier = 1.5 if green_num > 0 else 1.0
        else:
            multiplier = {0: 1.0, 1: 1.1, 2: 1.2, 3: 1.4, 4: 1.6}.get(green_num, 1.0)

        farm_pt = int(multiplier * (50 if small_harvest else 100))
        for i in range(5):
            harvest[i] = int(harvest[i] * multiplier)
        harvest.append(farm_pt)
        return harvest

    def maybe_harvest(self):
        """每4回合收菜"""
        if not (self.is_xiahesu() or self.turn >= 72 or self.turn % 4 == 3):
            return

        harvest = self.calculate_harvest_num(True)
        for i in range(5):
            self.add_dish_material(i, harvest[i])
        self.cook_farm_pt += harvest[5]

        # 清空
        for i in range(4):
            self.cook_harvest_history[i] = -1
            self.cook_harvest_green_history[i] = False
        for i in range(5):
            self.cook_harvest_extra[i] = 0

    def add_dish_material(self, idx: int, value: int):
        """增加菜材料，处理溢出"""
        limit = MATERIAL_LIMIT[self.cook_farm_level[idx]]
        self.cook_material[idx] = min(self.cook_material[idx] + value, limit)

    def add_training_level_count(self, train_idx: int, n: int):
        self.train_level_count[train_idx] += n
        if self.train_level_count[train_idx] > 16:
            self.train_level_count[train_idx] = 16

    def update_dish_pt_effects(self):
        """更新料理pt等级效果"""
        level = dish_pt_level(self.cook_dish_pt)
        self.cook_dishpt_success_rate = DISH_PT_BIG_SUCCESS_RATE[level]
        self.cook_dishpt_training_bonus = DISH_PT_TRAINING_BONUS[level]
        self.cook_dishpt_skillpt_bonus = DISH_PT_SKILL_PT_BONUS[level]
        self.cook_dishpt_deyilv_bonus = DISH_PT_DEYILV_BONUS[level]

    def check_dish_pt_upgrade(self):
        """检查料理pt升级"""
        old_pt = self.cook_dish_pt_turn_begin
        old_level = dish_pt_level(old_pt)
        new_level = dish_pt_level(self.cook_dish_pt)

        if old_level != new_level:
            self.update_dish_pt_effects()

        # 食意开眼：全体训练等级+1
        if (old_pt < 2000 and self.cook_dish_pt >= 2000) or \
           (old_pt < 7000 and self.cook_dish_pt >= 7000) or \
           (old_pt < 12000 and self.cook_dish_pt >= 12000):
            for i in range(5):
                self.add_training_level_count(i, 4)

        self.cook_dish_pt_turn_begin = self.cook_dish_pt

    def make_dish(self, dish_id: int) -> bool:
        """做菜"""
        if not self.is_dish_legal(dish_id):
            return False

        # 扣除材料
        for i in range(5):
            cost = DISH_COST[dish_id][i]
            if dish_id == DishType.g1plate:
                if self.cook_win_history[4] < 2:
                    cost = 100
            self.cook_material[i] -= cost

        self.cook_dish = dish_id

        # 自动升级农田
        self.auto_upgrade_farm(False)

        # 检查大成功
        is_big = self.cook_dish_sure_success or \
                 (self.rand.random() < 0.01 * self.cook_dishpt_success_rate)
        if is_big:
            self.handle_dish_big_success(dish_id)

        # 料理pt
        pt = DISH_GAIN_PT[dish_id]
        self.cook_dish_pt += pt

        self.cook_dish_sure_success = False
        # 跨越1500倍数或>12000，下次必大成功
        if self.cook_dish_pt >= 12000 or \
           self.cook_dish_pt // 1500 != self.cook_dish_pt_turn_begin // 1500:
            self.cook_dish_sure_success = True

        # 料理的训练加成以外效果
        level = DISH_LEVEL[dish_id]
        if level == 1:
            for i in range(6):
                self.add_jiaban(i, 2)
        elif level == 2:
            main_train = DISH_MAIN_TRAINING[dish_id]
            if self.cook_farm_level[main_train] >= 3:
                self.add_vital(5)
        elif level == 3:
            main_train = DISH_MAIN_TRAINING[dish_id]
            if main_train != 4:
                self.add_vital(10)
            if self.cook_farm_level[main_train] >= 3:
                self.add_vital(5)
        elif level == 4:
            self.add_vital(25)

        return True

    def handle_dish_big_success(self, dish_id: int):
        """处理料理大成功"""
        # hint
        self.dish_big_success_hint()
        # buff
        self.dish_big_success_get_buffs(dish_id)

    def dish_big_success_hint(self):
        """大成功-技能hint"""
        # 简化: 随机给一个hint
        person_idx = self.rand.randint(0, 5)
        self.persons[person_idx].hint_level += 1

    def dish_big_success_get_buffs(self, dish_id: int):
        """大成功-获取buff"""
        level = DISH_LEVEL[dish_id]
        for buff_type in range(1, 6):
            prob = BIG_SUCCESS_BUFF_PROB[level][buff_type]
            extra_prob = BIG_SUCCESS_BUFF_EXTRA_PROB[level][buff_type]
            total_prob = prob + extra_prob

            if self.rand.random() * 100 < total_prob:
                if buff_type == 1:  # 体力
                    self.add_vital(10)
                elif buff_type == 2:  # 心情
                    self.add_motivation(1)
                elif buff_type == 3:  # 羁绊
                    for i in range(6):
                        self.add_jiaban(i, 3)
                elif buff_type == 4:  # 分身
                    pass  # 简化: 分配一个支援卡到随机训练
                elif buff_type == 5:  # 体力上限
                    self.max_vital += 4

    def auto_upgrade_farm(self, before_xiahesu: bool):
        """自动升级农田"""
        strategy = 0  # 简化: 默认策略
        max_pt = self.max_farm_pt_until_now()

        while self.cook_farm_pt >= 100 and max_pt > 0:
            # 找最低等级的农田升级
            min_level = min(self.cook_farm_level)
            if min_level >= 5:
                break

            for i in range(5):
                if self.cook_farm_level[i] == min_level:
                    cost = FARM_LV_COST[self.cook_farm_level[i]]
                    if self.cook_farm_pt >= cost and self.cook_farm_level[i] < 5:
                        self.cook_farm_pt -= cost
                        self.cook_farm_level[i] += 1
                        break
            else:
                break
            max_pt = self.max_farm_pt_until_now()

    def get_dish_training_bonus(self, train_idx: int) -> int:
        """计算当前料理的训练加成"""
        if self.cook_dish == DishType.none:
            return 0
        if DISH_TRAINING_BONUS_EFFECTIVE[self.cook_dish][train_idx]:
            return self.cook_dishpt_training_bonus
        return 0

    def get_dish_race_bonus(self) -> int:
        """计算当前料理的比赛加成"""
        return 0  # 简化

    def add_status(self, idx: int, value: int):
        """加属性（考虑1200以上翻倍）"""
        if value <= 0:
            return
        current = self.five_status[idx]
        limit = FIVE_STATUS_LIMIT[idx]
        if current >= limit:
            return

        # 1200以上，每2点属性=1点实际
        if current >= 1200:
            actual = value // 2
        else:
            actual = value
            if current + actual > 1200:
                actual = (1200 - current) + (value - (1200 - current)) // 2

        self.five_status[idx] = min(current + actual, limit)

    def add_vital(self, value: int):
        self.vital = max(0, min(self.max_vital, self.vital + value))

    def add_motivation(self, value: int):
        self.motivation = max(1, min(5, self.motivation + value))

    def add_jiaban(self, idx: int, value: int):
        if idx < 6:
            self.persons[idx].friendship = max(0, min(100, self.persons[idx].friendship + value))
        elif idx == 6:
            self.friendship_noncard_yayoi = max(0, min(100, self.friendship_noncard_yayoi + value))
        elif idx == 7:
            self.friendship_noncard_reporter = max(0, min(100, self.friendship_noncard_reporter + value))

    def add_all_status(self, value: int):
        for i in range(5):
            self.add_status(i, value)

    def calculate_failure_rate(self, train_type: int) -> int:
        """计算失败率"""
        level = min(self.train_level[train_type] - 1, 4)
        base = FAIL_RATE_BASIC[train_type][level]

        # 干劲影响
        motivation_mod = (self.motivation - 3) * 30
        # 体力影响
        vital_mod = 0
        if self.vital < 30:
            vital_mod = 100
        elif self.vital < 50:
            vital_mod = 50

        rate = base - motivation_mod + vital_mod
        return max(0, min(10000, rate))

    def calculate_training_value(self, train_idx: int) -> Tuple[List[int], int, int]:
        """计算训练加成
        返回: (5维属性增益, pt增益, 失败率)
        """
        if train_idx < 0 or train_idx > 4:
            return [0]*5, 0, 0

        level = min(self.train_level[train_idx] - 1, 4)
        base = TRAINING_BASIC_VALUE[train_idx][level]

        gains = [0]*5
        for i in range(5):
            gains[i] = base[i]

        pt_gain = base[5]

        # 干劲倍率
        motivation_mult = 1.0 + 0.01 * self.cook_dishpt_deyilv_bonus
        if self.motivation >= 4:
            motivation_mult *= 1.1
        elif self.motivation <= 2:
            motivation_mult *= 0.9

        # 料理训练加成
        dish_bonus = self.get_dish_training_bonus(train_idx)
        for i in range(5):
            gains[i] = int(gains[i] * motivation_mult + dish_bonus)

        # 失败率
        fail_rate = self.calculate_failure_rate(train_idx)

        return gains, pt_gain, fail_rate

    def apply_training(self, train_idx: int) -> bool:
        """执行训练"""
        if train_idx < 0 or train_idx > 4:
            return False

        gains, pt_gain, fail_rate = self.calculate_training_value(train_idx)

        # 检查体力
        vital_cost = TRAINING_BASIC_VALUE[train_idx][min(self.train_level[train_idx]-1,4)][6]
        if self.vital + vital_cost < 0:
            return False

        # 失败检查
        if self.rand.random() * 10000 < fail_rate:
            # 大失败
            self.add_vital(vital_cost * 2)
            return False

        # 应用属性
        for i in range(5):
            self.add_status(i, gains[i])
        self.skill_point += pt_gain + self.cook_dishpt_skillpt_bonus
        self.add_vital(vital_cost)

        # 训练等级提升
        self.add_training_level_count(train_idx, 1)

        # 获得菜
        material_type = train_idx  # 训练类型对应菜种类
        is_green = self.rand.random() < 0.3  # 简化绿圈概率
        self.cook_train_material_type[train_idx] = material_type
        self.cook_train_green[train_idx] = is_green

        # 添加菜到收获历史
        harvest_idx = self.turn_idx_in_harvest_loop()
        if harvest_idx < 4:
            self.cook_harvest_history[harvest_idx] = material_type
            self.cook_harvest_green_history[harvest_idx] = is_green
            # 人头附加
            head_count = sum(1 for p in self.person_distribution[train_idx] if p >= 0 and p < 6)
            self.cook_harvest_extra[material_type] += head_count

        return True

    def next_turn(self):
        """进入下一回合"""
        # 收菜
        self.maybe_harvest()

        # 清空当前菜
        self.cook_dish = DishType.none

        # 检查料理pt升级
        self.check_dish_pt_upgrade()

        # 训练等级升级
        for i in range(5):
            if self.train_level_count[i] >= 4 and self.train_level[i] < 5:
                self.train_level_count[i] -= 4
                self.train_level[i] += 1

        self.turn += 1

    # ============================================================
    # 评分
    # ============================================================

    def get_skill_score(self) -> float:
        """技能分"""
        return self.skill_point * self.pt_score_rate

    def get_final_score(self) -> int:
        """最终评分"""
        score = 0
        for i in range(5):
            s = min(self.five_status[i], 2800)
            if FIVE_STATUS_FINAL_SCORE and s < len(FIVE_STATUS_FINAL_SCORE):
                score += FIVE_STATUS_FINAL_SCORE[s]
        score += int(self.get_skill_score())
        score += int(self.hint_pt_rate * sum(p.hint_level for p in self.persons))
        return score

    # ============================================================
    # 序列化
    # ============================================================

    def to_dict(self) -> dict:
        return {
            "turn": self.turn,
            "five_status": self.five_status,
            "skill_point": self.skill_point,
            "vital": self.vital,
            "max_vital": self.max_vital,
            "motivation": self.motivation,
            "train_level": self.train_level,
            "cook_material": self.cook_material,
            "cook_dish_pt": self.cook_dish_pt,
            "cook_farm_level": self.cook_farm_level,
            "cook_farm_pt": self.cook_farm_pt,
            "cook_dish": self.cook_dish,
            "cook_win_history": self.cook_win_history,
            "cook_dishpt_success_rate": self.cook_dishpt_success_rate,
            "cook_dishpt_training_bonus": self.cook_dishpt_training_bonus,
            "cook_dishpt_skillpt_bonus": self.cook_dishpt_skillpt_bonus,
            "final_score": self.get_final_score(),
        }

    def to_nn_input(self) -> List[float]:
        """转换为神经网络输入向量"""
        buf = []

        # 基本状态 (5+1+1+1+5+5 = 18)
        for s in self.five_status:
            buf.append(min(s, 2800) / 2800.0)
        buf.append(self.skill_point / 10000.0)
        buf.append(self.vital / self.max_vital)
        buf.append(self.motivation / 5.0)
        for lv in self.train_level:
            buf.append(lv / 5.0)
        for cnt in self.train_level_count:
            buf.append(cnt / 16.0)

        # 种田杯状态 (5+1+5+1+1+5+4+4+5+8+8+1 = 48)
        for m in self.cook_material:
            buf.append(m / 999.0)
        buf.append(min(self.cook_dish_pt_turn_begin, 12000) / 12000.0)
        for lv in self.cook_farm_level:
            for j in range(5):
                buf.append(1.0 if lv == j + 1 else 0.0)  # one-hot
        buf.append(self.cook_farm_pt * 0.002)
        # farm_pt阈值
        for thresh in [100, 180, 220, 250, 360, 440, 540, 660]:
            buf.append(1.0 if self.cook_farm_pt >= thresh else 0.0)

        buf.append(1.0 if self.cook_dish_sure_success else 0.0)

        # 当前菜 one-hot (14)
        for i in range(14):
            buf.append(1.0 if self.cook_dish == i else 0.0)

        # 试食会历史 (5*3=15)
        for h in self.cook_win_history:
            for j in range(3):
                buf.append(1.0 if h == j else 0.0)

        # 收获历史 (4*6=24)
        for i in range(4):
            mat = self.cook_harvest_history[i]
            for j in range(6):
                buf.append(1.0 if mat == j else 0.0)
            buf.append(1.0 if self.cook_harvest_green_history[i] else 0.0)
            buf.append(self.cook_harvest_extra[i] * 0.005)

        # 训练获得的菜 (8*6+8=56)
        for i in range(8):
            mat = self.cook_train_material_type[i]
            for j in range(6):
                buf.append(1.0 if mat == j else 0.0)
            buf.append(1.0 if self.cook_train_green[i] else 0.0)

        # 比赛菜 (6)
        for j in range(6):
            buf.append(1.0 if self.cook_main_race_material_type == j else 0.0)

        # 料理pt等级效果 (4)
        buf.append(self.cook_dishpt_success_rate * 0.01)
        buf.append(self.cook_dishpt_training_bonus * 0.01)
        buf.append(self.cook_dishpt_skillpt_bonus * 0.01)
        buf.append(self.cook_dishpt_deyilv_bonus * 0.05)

        return buf

    @classmethod
    def from_dict(cls, d: dict) -> 'CookGame':
        g = cls()
        g.turn = d.get("turn", 0)
        g.five_status = d.get("five_status", [0]*5)
        g.skill_point = d.get("skill_point", 0)
        g.vital = d.get("vital", 100)
        g.max_vital = d.get("max_vital", 100)
        g.motivation = d.get("motivation", 3)
        g.train_level = d.get("train_level", [1]*5)
        g.cook_material = d.get("cook_material", [0]*5)
        g.cook_dish_pt = d.get("cook_dish_pt", 0)
        g.cook_farm_level = d.get("cook_farm_level", [1]*5)
        g.cook_farm_pt = d.get("cook_farm_pt", 0)
        g.cook_dish = d.get("cook_dish", 0)
        g.cook_win_history = d.get("cook_win_history", [0]*5)
        g.update_dish_pt_effects()
        return g


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    rand = random.Random(42)
    game = CookGame(rand)
    game.chara_id = 1001
    game.chara_stars = 5

    print("=== 种田杯模拟器测试 ===")
    print(f"初始状态: turn={game.turn}, vital={game.vital}, motivation={game.motivation}")
    print(f"农田等级: {game.cook_farm_level}")
    print(f"NN输入维度: {len(game.to_nn_input())}")

    # 模拟78回合
    for turn in range(TOTAL_TURN):
        # 简单策略: 优先做菜，然后训练
        legal_dishes = [d for d in range(1, 14) if game.is_dish_legal(d)]
        if legal_dishes:
            dish = rand.choice(legal_dishes)
            game.make_dish(dish)

        # 训练
        best_train = rand.randint(0, 4)
        game.apply_training(best_train)

        game.next_turn()

    print(f"\n最终状态: turn={game.turn}")
    print(f"五维: {game.five_status}")
    print(f"技能pt: {game.skill_point}")
    print(f"最终评分: {game.get_final_score()}")
    print(f"料理pt: {game.cook_dish_pt}")
    print(f"农田等级: {game.cook_farm_level}")
    print(f"试食会历史: {game.cook_win_history}")
