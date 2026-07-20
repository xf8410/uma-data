"""Reproducible rule-distillation training for the fixed Cook scenario.

No generated samples are committed. Labels are produced from the pre-action state,
policy has separate dish/main heads, and the final complete-run return is filled
back into every state in that run. Seeds are split by whole run.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, random, statistics, time
from pathlib import Path
import numpy as np
from simulator import CookSimulator

DISH_N, MAIN_N, INPUT_N = 14, 8, 128

def heuristic(sim:CookSimulator, explore:float=0.0):
    rng=sim.rng
    dishes=sim.legal_dishes(); dish=0
    if len(dishes)>1:
        def dv(d):
            # Reserve G1 plate until late; value training-specialised dishes when affordable.
            return (40 if d==13 and sim.s.turn>=72 else 0)+d+(8 if d>=8 else 0)-sum(sim.s.materials[i]<2*c for i,c in enumerate(__import__('simulator').DISH_COST[d]))*5
        dish=max(dishes,key=dv)
        if rng.random()<.45:dish=0
    legal=sim.legal_main()
    if sim.forced_race:main=7
    elif sim.s.vital<28:main=5 if rng.random()<.75 else 6
    else:
        vals=[]
        for a in legal:
            if a<5:
                g,pt,fail=sim.training_preview(a); v=sum(g)+2*pt-80*fail+sum(p==a for p in sim.s.support_pos)*8
            elif a==5:v=max(0,65-sim.s.vital)*.55
            elif a==6:v=max(0,50-sim.s.vital)*.35+8*(sim.s.motivation<4)
            else:v=20 if sim.s.turn>60 else -5
            vals.append((v,a))
        main=max(vals)[1]
    if explore and rng.random()<explore:dish=rng.choice(dishes)
    if explore and rng.random()<explore:main=rng.choice(legal)
    return dish,main

def rollout(seed:int, policy='rule', model=None, explore=0.0, collect=False):
    sim=CookSimulator(seed); hist=[]
    while not sim.done:
        feat=np.asarray(sim.features(),dtype=np.float32)
        if policy=='random':
            dish=sim.rng.choice(sim.legal_dishes()); main=sim.rng.choice(sim.legal_main())
        elif model is None:dish,main=heuristic(sim,explore)
        else:
            import torch
            with torch.no_grad():dlog,mlog,_=model(torch.from_numpy(feat[None,:]))
            dishes=sim.legal_dishes(); mains=sim.legal_main()
            dish=max(dishes,key=lambda x:float(dlog[0,x])); main=max(mains,key=lambda x:float(mlog[0,x]))
        if collect:hist.append((feat,dish,main))
        sim.step(dish,main)
    return sim.score(),hist,sim.s

def generate(games:int,seed0:int):
    rows=[]; scores=[]
    for seed in range(seed0,seed0+games):
        score,h,_=rollout(seed,explore=.08,collect=True); scores.append(score)
        value=score/20000.0
        rows.extend((x,d,m,value) for x,d,m in h)
    x=np.stack([r[0] for r in rows]); d=np.asarray([r[1] for r in rows]); m=np.asarray([r[2] for r in rows]); v=np.asarray([r[3] for r in rows],dtype=np.float32)
    return x,d,m,v,scores

def stats(values):
    a=sorted(values); q=lambda p:a[min(len(a)-1,int(p*(len(a)-1)))]
    return {'n':len(a),'mean':statistics.fmean(a),'stdev':statistics.pstdev(a),'min':a[0],'p10':q(.1),'median':q(.5),'p90':q(.9),'max':a[-1]}

def train(args):
    import torch, torch.nn as nn
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    class Model(nn.Module):
        def __init__(self):
            super().__init__(); self.body=nn.Sequential(nn.Linear(INPUT_N,192),nn.ReLU(),nn.Linear(192,192),nn.ReLU(),nn.Linear(192,128),nn.ReLU()); self.dish=nn.Linear(128,DISH_N); self.main=nn.Linear(128,MAIN_N); self.value=nn.Linear(128,1)
        def forward(self,x):h=self.body(x);return self.dish(h),self.main(h),self.value(h).squeeze(-1)
    x,d,m,v,train_scores=generate(args.games,args.seed)
    model=Model(); opt=torch.optim.AdamW(model.parameters(),lr=2e-3,weight_decay=1e-4)
    xt=torch.from_numpy(x); dt=torch.from_numpy(d); mt=torch.from_numpy(m); vt=torch.from_numpy(v)
    n=len(x); rng=np.random.default_rng(args.seed)
    for epoch in range(args.epochs):
        order=rng.permutation(n); losses=[]; model.train()
        for start in range(0,n,args.batch):
            idx=torch.from_numpy(order[start:start+args.batch]); dl,ml,pv=model(xt[idx]); loss=nn.functional.cross_entropy(dl,dt[idx])+nn.functional.cross_entropy(ml,mt[idx])+2*nn.functional.smooth_l1_loss(pv,vt[idx]); opt.zero_grad();loss.backward();opt.step();losses.append(float(loss))
        print(f'epoch={epoch+1} loss={statistics.fmean(losses):.5f}',flush=True)
    model.eval(); out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    val_seeds=range(args.seed+1_000_000,args.seed+1_000_000+args.validation_games)
    random_scores=[rollout(s,policy='random',model=None,explore=1.0)[0] for s in val_seeds]
    rule_scores=[rollout(s)[0] for s in val_seeds]
    model_scores=[rollout(s,model=model)[0] for s in val_seeds]
    report={'scenario_id':8,'card_id':101101,'seed':args.seed,'whole_run_split':True,'train_games':args.games,'train_samples':len(x),'train_score':stats(train_scores),'validation_seeds':[val_seeds.start,val_seeds.stop-1],'random_baseline':stats(random_scores),'rule_baseline':stats(rule_scores),'model':stats(model_scores),'event_model':'explicit statistical generic and Grass Wonder channels'}
    torch.save({'state_dict':model.state_dict(),'input_dim':INPUT_N,'dish_dim':DISH_N,'main_dim':MAIN_N},out/'cook_model_state_dict.pt')
    dummy=torch.zeros(1,INPUT_N)
    torch.onnx.export(model,dummy,out/'cook_model.onnx',input_names=['state'],output_names=['dish_logits','main_logits','value'],dynamic_axes={'state':{0:'batch'},'dish_logits':{0:'batch'},'main_logits':{0:'batch'},'value':{0:'batch'}},opset_version=17,external_data=False)
    import onnxruntime as ort
    sess=ort.InferenceSession(str(out/'cook_model.onnx'),providers=['CPUExecutionProvider']); probe=np.random.default_rng(args.seed+9).normal(size=(7,INPUT_N)).astype('float32')
    with torch.no_grad():pt=[z.numpy() for z in model(torch.from_numpy(probe))]
    ox=sess.run(None,{'state':probe}); report['onnx_max_abs_error']=max(float(np.max(np.abs(a-b))) for a,b in zip(pt,ox))
    report['onnx_sha256']=hashlib.sha256((out/'cook_model.onnx').read_bytes()).hexdigest(); report['onnx_bytes']=(out/'cook_model.onnx').stat().st_size
    (out/'training_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'model_manifest.json').write_text(json.dumps({'scenario_id':8,'card_id':101101,'input':{'name':'state','shape':['batch',INPUT_N]},'outputs':[{'name':'dish_logits','shape':['batch',DISH_N]},{'name':'main_logits','shape':['batch',MAIN_N]},{'name':'value','shape':['batch']}],'sha256':report['onnx_sha256'],'single_file':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument('--games',type=int,default=2000);p.add_argument('--validation-games',type=int,default=200);p.add_argument('--epochs',type=int,default=20);p.add_argument('--batch',type=int,default=512);p.add_argument('--seed',type=int,default=20260720);p.add_argument('--output',default=str(Path(__file__).parent/'artifacts'));train(p.parse_args())
if __name__=='__main__':main()
