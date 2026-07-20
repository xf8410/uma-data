"""Compare legal 1 speed / 1 power / 2 guts / 1 wit / director decks.
Uses identical whole-run seeds for every deck; writes only aggregate results.
"""
from __future__ import annotations
import argparse,itertools,json,statistics
from pathlib import Path
from simulator import CookSimulator, DISH_COST

def heuristic(sim):
    dishes=sim.legal_dishes();dish=0
    if len(dishes)>1:
        def dv(d):return (40 if d==13 and sim.s.turn>=72 else 0)+d+(8 if d>=8 else 0)-sum(sim.s.materials[i]<2*c for i,c in enumerate(DISH_COST[d]))*5
        dish=max(dishes,key=dv)
        if sim.rng.random()<.45:dish=0
    legal=sim.legal_main()
    if sim.forced_race:main=7
    elif sim.s.friend_stage>=2 and sim.s.friend_outings<5 and sim.s.vital<70:main=6
    elif sim.s.vital<28:main=5 if sim.rng.random()<.75 else 6
    else:
        vals=[]
        for a in legal:
            if a<5:
                g,pt,fail=sim.training_preview(a);v=sum(g)+2*pt-80*fail+sum(p==a for p in sim.s.support_pos)*8
            elif a==5:v=max(0,65-sim.s.vital)*.55
            elif a==6:v=max(0,50-sim.s.vital)*.35+8*(sim.s.motivation<4)
            else:v=20 if sim.s.turn>60 else -5
            vals.append((v,a))
        main=max(vals)[1]
    return dish,main

SPEED=(30161,30242,30275,30282,30302,30298)
POWER=(30283,30277)
GUTS=(30264,30293,30294)
WIT=(30289,30248)
DIRECTOR=30207

def run(deck,seeds):
    values=[]
    for seed in seeds:
        g=CookSimulator(seed,deck)
        while not g.done:
            d,a=heuristic(g);g.step(d,a)
        values.append(g.score())
    a=sorted(values)
    return {'n':len(a),'mean':statistics.fmean(a),'stdev':statistics.pstdev(a),'p10':a[int(.1*(len(a)-1))],'median':a[int(.5*(len(a)-1))],'p90':a[int(.9*(len(a)-1))],'max':a[-1]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--games',type=int,default=100);p.add_argument('--seed',type=int,default=20260720);p.add_argument('--output',default=str(Path(__file__).parent/'deck_benchmark.json'));args=p.parse_args()
    seeds=range(args.seed,args.seed+args.games);results=[]
    for s,power,guts,wit in itertools.product(SPEED,POWER,itertools.combinations(GUTS,2),WIT):
        # character-level duplicate: Daring Tact 30293 guts conflicts with 30248 wit.
        if 30293 in guts and wit==30248:continue
        deck=(s,power,*guts,wit,DIRECTOR);st=run(deck,seeds);results.append({'deck':deck,'stats':st});print(deck,round(st['mean'],1),st['max'],flush=True)
    results.sort(key=lambda x:x['stats']['mean'],reverse=True)
    out={'seed_range':[args.seed,args.seed+args.games-1],'games_per_deck':args.games,'legal_decks':len(results),'score_source':'FiveStatusFinalScore + 2*skill_pt + initial unique score; raw evaluation only','results':results}
    Path(args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('BEST',results[0])
if __name__=='__main__':main()
