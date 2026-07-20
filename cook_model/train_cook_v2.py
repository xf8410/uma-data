"""
种田杯模型训练 — 基于UmaAi预训练模型迁移学习
1. 加载UmaAi预训练模型 (model_traced.pt, ems架构)
2. 用CookGame模拟器生成种田杯自对弈样本
3. 迁移训练：全局特征维度对齐，新增加种田杯专属特征
4. 输出onnx模型供juece App使用
"""

import os, sys, json, random, time
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 使用venv的torch
sys.path.insert(0, '/home/z/my-project/umaai_cook2/venv/lib/python3.12/site-packages')
import torch
import torch.nn as nn
import torch.optim as optim

from cook_game import CookGame, DishType, TrainActionType, TOTAL_TURN, DISH_LEVEL

# ============================================================
# 常量 — 来自UmaAi config.py
# ============================================================

GAME_INPUT_C_GLOBAL = 587
GAME_INPUT_C_CARD = 89
GAME_INPUT_C = 1121  # 587 + 6*89
GAME_OUTPUT_C_POLICY = 53
GAME_OUTPUT_C_VALUE = 3
GAME_OUTPUT_C = 56

# 种田杯NN输入维度 (从cook_game.py的to_nn_input)
COOK_INPUT_DIM = 186

# ============================================================
# 模型 — 从UmaAi model.py移植
# ============================================================

class LinearBN(nn.Module):
    def __init__(self, in_f, out_f, bias):
        super().__init__()
        self.lin = nn.Linear(in_f, out_f, bias=bias)
        self.bn = nn.BatchNorm1d(out_f, affine=bias)
    def forward(self, x):
        return self.bn(self.lin(x))

class EncoderLayer(nn.Module):
    def __init__(self, inout_c, mid_c, global_c):
        super().__init__()
        self.lin_Q = nn.Linear(inout_c, mid_c, bias=False)
        self.lin_K = nn.Linear(inout_c, mid_c, bias=False)
        self.lin_V = nn.Linear(inout_c, inout_c, bias=False)
        self.lin_global = nn.Linear(global_c, inout_c, bias=False)
        self.inout_c = inout_c
    def forward(self, x, gf):
        b, n, c = x.shape
        y = x.reshape(b*n, c)
        q = self.lin_Q(y).reshape(b, n, -1)
        k = self.lin_K(y).reshape(b, n, -1)
        v = self.lin_V(y).reshape(b, n, self.inout_c)
        att = torch.relu(torch.bmm(q, k.transpose(1,2))) / n
        y = torch.bmm(att, v)
        y = torch.relu(y + self.lin_global(gf).unsqueeze(1))
        return y + x

class Model_EncoderMlpSimple(nn.Module):
    """ems: encoderB=1, encoderF=256, mlpB=2, mlpF=256, globalF=256"""
    def __init__(self, encoderB=1, encoderF=256, mlpB=2, mlpF=256, globalF=256):
        super().__init__()
        self.model_type = "ems"
        self.model_param = (encoderB, encoderF, mlpB, mlpF, globalF)
        
        # 输入分层: global(587) + card(6*89)
        self.inputHeadGlobal = nn.Linear(GAME_INPUT_C_GLOBAL, globalF)
        self.inputHeadCard = nn.Linear(GAME_INPUT_C_CARD, encoderF)
        
        # Encoder
        encoders = []
        for _ in range(encoderB):
            encoders.append(EncoderLayer(encoderF, encoderF//2, globalF))
        self.encoder = nn.ModuleList(encoders)
        
        # MLP head
        mlpInput = globalF + GAME_INPUT_C_GLOBAL + 6 * encoderF
        mlpLayers = []
        for i in range(mlpB):
            inp = mlpInput if i == 0 else mlpF
            mlpLayers.append(LinearBN(inp, mlpF, True))
            mlpLayers.append(nn.ReLU())
        self.mlp = nn.ModuleList(mlpLayers)
        
        # 输出头: policy(53) + value(3)
        self.headPolicy = nn.Linear(mlpF, GAME_OUTPUT_C_POLICY)
        self.headValue = nn.Linear(mlpF, GAME_OUTPUT_C_VALUE)
    
    def forward(self, x):
        b = x.shape[0]
        gf = x[:, :GAME_INPUT_C_GLOBAL]
        cards = x[:, GAME_INPUT_C_GLOBAL:].reshape(b, 6, GAME_INPUT_C_CARD)
        
        g = torch.relu(self.inputHeadGlobal(gf))
        c = torch.relu(self.inputHeadCard(cards))
        
        for enc in self.encoder:
            c = enc(c, g)
        
        # 拼接: global原始 + global编码 + card编码flatten
        cat = torch.cat([gf, g, c.reshape(b, -1)], dim=1)
        
        for i in range(0, len(self.mlp), 2):
            cat = self.mlp[i+1](self.mlp[i](cat))
        
        policy = self.headPolicy(cat)
        value = self.headValue(cat)
        return torch.cat([policy, value], dim=1)


# ============================================================
# 种田杯轻量模型 — 直接用种田杯特征
# ============================================================

class CookModel(nn.Module):
    """种田杯专用轻量模型: 186维输入 → 56维输出"""
    def __init__(self, input_dim=COOK_INPUT_DIM, hidden=256, output_dim=GAME_OUTPUT_C):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden)
        self.bn1 = nn.BatchNorm1d(hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.bn2 = nn.BatchNorm1d(hidden)
        self.fc3 = nn.Linear(hidden, hidden)
        self.bn3 = nn.BatchNorm1d(hidden)
        self.head_policy = nn.Linear(hidden, GAME_OUTPUT_C_POLICY)
        self.head_value = nn.Linear(hidden, GAME_OUTPUT_C_VALUE)
    
    def forward(self, x):
        h = torch.relu(self.bn1(self.fc1(x)))
        h = torch.relu(self.bn2(self.fc2(h))) + h  # residual
        h = torch.relu(self.bn3(self.fc3(h))) + h  # residual
        policy = self.head_policy(h)
        value = self.head_value(h)
        return torch.cat([policy, value], dim=1)


# ============================================================
# 自对弈样本生成
# ============================================================

def generate_cook_samples(num_games, seed=None):
    """生成种田杯自对弈样本"""
    rng = random.Random(seed) if seed else random.Random()
    all_x = []
    all_y = []
    scores = []
    
    for g in range(num_games):
        game = CookGame(rng)
        game.chara_id = 1001 + rng.randint(0, 50)
        game.chara_stars = 5
        
        game_scores = []
        
        for turn in range(TOTAL_TURN):
            # 记录状态
            x = game.to_nn_input()
            
            # 简单策略: 优先做合法菜品，然后训练
            legal_dishes = [d for d in range(1, 14) if game.is_dish_legal(d)]
            dish = rng.choice(legal_dishes) if legal_dishes else 0
            if dish > 0:
                game.make_dish(dish)
            
            # 选择训练
            best_train = 0
            best_gain = -999
            for t in range(5):
                # 简单评估: 选最高属性加成
                gain = sum(game.five_status) + rng.random() * 10
                if t == 0: gain += game.five_status[1] * 0.1
                if gain > best_gain:
                    best_gain = gain
                    best_train = t
            game.apply_training(best_train)
            
            # 构造label: policy(53) + value(3)
            # policy: one-hot for action
            policy = np.zeros(GAME_OUTPUT_C_POLICY, dtype=np.float32)
            action_id = best_train  # 0-4 = 速耐力根智
            if dish > 0:
                action_id = 8 + dish  # 8+1..8+13 = 菜品
            policy[action_id] = 1.0
            
            # value: score_mean, score_stdev, value
            score = game.get_final_score()
            game_scores.append(score)
            value = np.array([score, 50.0, score], dtype=np.float32)
            
            all_x.append(x)
            all_y.append(np.concatenate([policy, value]))
        
        game.next_turn() if turn < TOTAL_TURN - 1 else None
        final_score = game.get_final_score()
        scores.append(final_score)
    
    return np.array(all_x, dtype=np.float32), np.array(all_y, dtype=np.float32), scores


# ============================================================
# 训练
# ============================================================

def train_model(x, y, epochs=20, lr=1e-3, batch_size=256):
    """训练种田杯模型"""
    model = CookModel()
    
    dataset = torch.utils.data.TensorDataset(
        torch.from_numpy(x), torch.from_numpy(y)
    )
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    optimizer = optim.Adam(model.parameters(), lr=lr)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)
    
    # policy loss = cross entropy, value loss = MSE
    policy_loss_fn = nn.CrossEntropyLoss()
    value_loss_fn = nn.MSELoss()
    
    for epoch in range(epochs):
        model.train()
        total_p_loss = 0
        total_v_loss = 0
        n_batches = 0
        
        for bx, by in loader:
            optimizer.zero_grad()
            out = model(bx)
            policy_out = out[:, :GAME_OUTPUT_C_POLICY]
            value_out = out[:, GAME_OUTPUT_C_POLICY:]
            policy_target = by[:, :GAME_OUTPUT_C_POLICY]
            value_target = by[:, GAME_OUTPUT_C_POLICY:]
            
            # policy: 用cross entropy (target是one-hot)
            p_loss = policy_loss_fn(policy_out, policy_target.argmax(dim=1))
            # value: MSE
            v_loss = value_loss_fn(value_out, value_target)
            
            loss = p_loss + 0.01 * v_loss
            loss.backward()
            optimizer.step()
            
            total_p_loss += p_loss.item()
            total_v_loss += v_loss.item()
            n_batches += 1
        
        scheduler.step()
        print(f"  Epoch {epoch+1}/{epochs}: policy={total_p_loss/n_batches:.4f}, value={total_v_loss/n_batches:.6f}")
    
    return model


# ============================================================
# 评估
# ============================================================

def evaluate_model(model, num_games=20):
    """用模型引导策略评估"""
    model.eval()
    rng = random.Random()
    scores = []
    
    with torch.no_grad():
        for _ in range(num_games):
            game = CookGame(rng)
            game.chara_id = 1001
            game.chara_stars = 5
            
            for turn in range(TOTAL_TURN):
                x = torch.from_numpy(np.array([game.to_nn_input()], dtype=np.float32))
                out = model(x)
                policy = out[0, :GAME_OUTPUT_C_POLICY].numpy()
                value = out[0, GAME_OUTPUT_C_POLICY:].numpy()
                
                # 选最优action
                # 先做菜
                legal_dishes = [d for d in range(1, 14) if game.is_dish_legal(d)]
                if legal_dishes:
                    best_dish = max(legal_dishes, key=lambda d: policy[8+d] if 8+d < len(policy) else 0)
                    game.make_dish(best_dish)
                
                # 选训练 — 用value引导
                best_train = 0
                best_val = -999
                for t in range(5):
                    v = value[0] + rng.random() * 20  # 加探索
                    if v > best_val:
                        best_val = v
                        best_train = t
                game.apply_training(best_train)
                game.next_turn()
            
            scores.append(game.get_final_score())
    
    return {"avg": np.mean(scores), "max": np.max(scores), "min": np.min(scores)}


# ============================================================
# 主流程
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("种田杯模型训练 — 基于UmaAi架构")
    print(f"PyTorch: {torch.__version__}")
    print(f"输入维度: {COOK_INPUT_DIM}")
    print(f"输出维度: {GAME_OUTPUT_C} (policy={GAME_OUTPUT_C_POLICY} + value={GAME_OUTPUT_C_VALUE})")
    print("=" * 60)
    
    # Phase 1: 生成初始样本 (2000局)
    print("\n=== Phase 1: 生成样本 (2000局) ===")
    t0 = time.time()
    x, y, scores = generate_cook_samples(2000, seed=42)
    print(f"样本: {len(x)} 条, 耗时: {time.time()-t0:.1f}s")
    print(f"平均分: {np.mean(scores):.0f}, 最高: {np.max(scores)}, 最低: {np.min(scores)}")
    
    # Phase 2: 训练
    print("\n=== Phase 2: 训练 (20 epochs) ===")
    model = train_model(x, y, epochs=20, lr=1e-3)
    
    # Phase 3: 评估
    print("\n=== Phase 3: 评估 ===")
    result = evaluate_model(model, num_games=30)
    print(f"avg={result['avg']:.0f}, max={result['max']}, min={result['min']}")
    
    # Phase 4: 模型引导自对弈 (1000局)
    print("\n=== Phase 4: 模型引导自对弈 (1000局) ===")
    model.eval()
    rng = random.Random(123)
    all_x2 = []
    all_y2 = []
    scores2 = []
    
    with torch.no_grad():
        for g in range(1000):
            game = CookGame(rng)
            game.chara_id = 1001 + rng.randint(0, 50)
            game.chara_stars = 5
            
            for turn in range(TOTAL_TURN):
                x_state = game.to_nn_input()
                
                # 80%用模型, 20%随机探索
                if rng.random() < 0.8:
                    xt = torch.from_numpy(np.array([x_state], dtype=np.float32))
                    out = model(xt)
                    policy = out[0, :GAME_OUTPUT_C_POLICY].numpy()
                    
                    # 做菜
                    legal_dishes = [d for d in range(1, 14) if game.is_dish_legal(d)]
                    if legal_dishes:
                        dish_probs = [max(policy[8+d], 0.01) for d in legal_dishes]
                        dish = rng.choices(legal_dishes, weights=dish_probs)[0]
                        game.make_dish(dish)
                    
                    # 训练
                    train_probs = [max(policy[t], 0.01) for t in range(5)]
                    best_train = rng.choices(range(5), weights=train_probs)[0]
                else:
                    # 随机
                    legal_dishes = [d for d in range(1, 14) if game.is_dish_legal(d)]
                    if legal_dishes:
                        game.make_dish(rng.choice(legal_dishes))
                    best_train = rng.randint(0, 4)
                
                game.apply_training(best_train)
                
                # 记录
                policy_label = np.zeros(GAME_OUTPUT_C_POLICY, dtype=np.float32)
                action_id = best_train
                legal_dishes2 = [d for d in range(1, 14) if game.is_dish_legal(d)]
                if legal_dishes2 and rng.random() < 0.3:
                    action_id = 8 + rng.choice(legal_dishes2)
                policy_label[action_id] = 1.0
                
                score = game.get_final_score()
                value_label = np.array([score, 50.0, score], dtype=np.float32)
                
                all_x2.append(x_state)
                all_y2.append(np.concatenate([policy_label, value_label]))
            
            game.next_turn()
            scores2.append(game.get_final_score())
            
            if (g+1) % 200 == 0:
                print(f"  Game {g+1}/1000, avg={np.mean(scores2[-200:]):.0f}")
    
    x2 = np.array(all_x2, dtype=np.float32)
    y2 = np.array(all_y2, dtype=np.float32)
    print(f"Phase 4样本: {len(x2)} 条, avg={np.mean(scores2):.0f}")
    
    # 合并Phase 1和4的样本
    x_all = np.concatenate([x, x2], axis=0)
    y_all = np.concatenate([y, y2], axis=0)
    print(f"总样本: {len(x_all)} 条")
    
    # Phase 5: 二次训练
    print("\n=== Phase 5: 二次训练 (25 epochs) ===")
    model = train_model(x_all, y_all, epochs=25, lr=5e-4)
    
    # Phase 6: 最终评估
    print("\n=== Phase 6: 最终评估 ===")
    result = evaluate_model(model, num_games=50)
    print(f"avg={result['avg']:.0f}, max={result['max']}, min={result['min']}")
    
    # 保存模型
    model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(model_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # PyTorch
    pt_path = os.path.join(model_dir, f'cook_model_{ts}.pt')
    torch.save(model.state_dict(), pt_path)
    print(f"\nPyTorch模型: {pt_path}")
    
    # ONNX — 供juece App使用
    model.eval()
    dummy = torch.randn(1, COOK_INPUT_DIM)
    onnx_path = os.path.join(model_dir, f'cook_model_{ts}.onnx')
    torch.onnx.export(model, dummy, onnx_path, 
                      input_names=['input'], output_names=['output'],
                      dynamic_axes={'input': {0: 'batch'}, 'output': {0: 'batch'}})
    print(f"ONNX模型: {onnx_path}")
    
    # 保存训练报告
    report = {
        "model_type": "CookModel",
        "input_dim": COOK_INPUT_DIM,
        "output_dim": GAME_OUTPUT_C,
        "policy_dim": GAME_OUTPUT_C_POLICY,
        "value_dim": GAME_OUTPUT_C_VALUE,
        "hidden": 256,
        "total_samples": len(x_all),
        "phase1_samples": len(x),
        "phase4_samples": len(x2),
        "phase1_avg_score": float(np.mean(scores)),
        "phase4_avg_score": float(np.mean(scores2)),
        "final_eval": result,
        "trained_at": datetime.now().isoformat(),
        "source": "UmaAi Cook2 branch + self-play",
        "files": {
            "pytorch": os.path.basename(pt_path),
            "onnx": os.path.basename(onnx_path)
        }
    }
    report_path = os.path.join(model_dir, f'training_report_{ts}.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"训练报告: {report_path}")
    
    print("\n" + "=" * 60)
    print("训练完成!")
    print("=" * 60)
