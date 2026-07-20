"""Deterministic, testable Cook scenario simulator for fixed 5-star Grass Wonder.

This is an explicit statistical simulator, not a claim to reproduce game-server RNG.
Cook mechanics and turn ordering follow UmaAi Cook2. Character-event effects are
modelled separately from generic events so they cannot silently disappear.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import copy, random
from typing import List, Tuple

SCENARIO_ID = 8
TOTAL_TURNS = 78
CARD_ID = 101101
INITIAL_STATUS = (118, 91, 129, 96, 116)
GROWTH = (20, 0, 10, 0, 0)
TARGET_RACES = frozenset((11, 22, 33, 45, 47, 59, 66, 71, 73, 75, 77))
DISH_COST = (
 (0,0,0,0,0),(25,0,50,0,50),(25,50,0,50,0),(150,0,80,0,0),
 (0,150,0,80,0),(0,80,150,0,0),(40,0,40,150,0),(80,0,0,0,150),
 (250,0,80,0,0),(0,250,0,80,0),(0,80,250,0,0),(40,0,40,250,0),
 (80,0,0,0,250),(80,80,80,80,80))
DISH_UNLOCK = (99,0,0,0,0,0,0,0,48,48,48,48,48,72)
DISH_PT = (0,250,250,500,500,500,500,500,800,800,800,800,800,1500)
# speed, stamina, power, guts, wisdom, skill points, vitality
TRAIN_BASE = (
 (12,0,3,0,0,5,-20),(0,10,0,6,0,5,-21),(0,5,11,0,0,5,-21),
 (3,0,3,12,0,5,-22),(3,0,0,0,10,7,5))
# Six abstract support slots. Type, training bonus, friendship bonus, initial bond.
SUPPORTS = ((0,8,22,30),(0,6,20,25),(2,8,22,30),(2,6,20,25),(4,8,22,30),(3,6,20,25))

@dataclass
class State:
    seed: int
    turn: int = 0
    status: List[int] = field(default_factory=lambda:list(INITIAL_STATUS))
    skill_pt: int = 0
    vital: int = 100
    max_vital: int = 100
    motivation: int = 3
    materials: List[int] = field(default_factory=lambda:[0]*5)
    farm_level: List[int] = field(default_factory=lambda:[1]*5)
    farm_pt: int = 0
    dish_pt: int = 0
    active_dish: int = 0
    bond: List[int] = field(default_factory=lambda:[x[3] for x in SUPPORTS])
    support_pos: List[int] = field(default_factory=lambda:[-1]*6)
    event_counts: List[int] = field(default_factory=lambda:[0,0,0]) # fixed,generic,chara
    race_count: int = 0
    failed_trainings: int = 0
    rng_state: object = None

class CookSimulator:
    def __init__(self, seed:int):
        self.rng=random.Random(seed)
        self.s=State(seed=seed)
        self._distribute()
        self.s.rng_state=self.rng.getstate()

    def clone(self):
        x=copy.deepcopy(self); x.rng=random.Random(); x.rng.setstate(self.rng.getstate()); return x

    @property
    def forced_race(self): return self.s.turn in TARGET_RACES
    @property
    def done(self): return self.s.turn >= TOTAL_TURNS

    def legal_dishes(self):
        out=[0]
        if self.s.active_dish: return out
        for d in range(1,14):
            if self.s.turn < DISH_UNLOCK[d]: continue
            cost=list(DISH_COST[d])
            if d==13 and self.s.dish_pt<10000: cost=[100]*5
            if all(a>=b for a,b in zip(self.s.materials,cost)): out.append(d)
        return out

    def legal_main(self):
        if self.forced_race: return [7]
        out=[5,6]
        for t in range(5):
            fail=self.training_preview(t)[2]
            if self.s.vital>8 or t==4: out.append(t)
        out.append(7) # optional race
        return sorted(set(out))

    def make_dish(self,d:int):
        if d not in self.legal_dishes(): raise ValueError('illegal dish')
        if d==0:return
        cost=list(DISH_COST[d])
        if d==13 and self.s.dish_pt<10000: cost=[100]*5
        self.s.materials=[a-b for a,b in zip(self.s.materials,cost)]
        self.s.dish_pt+=DISH_PT[d]; self.s.active_dish=d
        # Cook2 statistical success model.
        rate=min(1.0, .15 + self.s.dish_pt/48000)
        if self.rng.random()<rate:
            self.s.vital=min(self.s.max_vital,self.s.vital+10)
            self.s.motivation=min(5,self.s.motivation+1)

    def training_preview(self,t:int)->Tuple[List[int],int,float]:
        b=TRAIN_BASE[t]; people=[i for i,p in enumerate(self.s.support_pos) if p==t]
        shine=sum(self.s.bond[i]>=80 and SUPPORTS[i][0]==t for i in people)
        bonus=sum(SUPPORTS[i][1] for i in people)
        friend=sum(SUPPORTS[i][2] for i in people if self.s.bond[i]>=80 and SUPPORTS[i][0]==t)
        dish_bonus=0
        if self.s.active_dish:
            main=(self.s.active_dish-3)%5 if 3<=self.s.active_dish<=12 else -1
            dish_bonus=8+(12 if main==t else 0)+(8 if self.s.active_dish==13 else 0)
        mood=(.8,.9,1.0,1.1,1.2)[max(0,min(4,self.s.motivation-1))]
        mult=mood*(1+bonus/100)*(1+friend/100)
        gain=[max(0,int(v*mult + (dish_bonus if v else 0))) for v in b[:5]]
        gain[t]=int(gain[t]*(1+GROWTH[t]/100))
        pt=max(0,int(b[5]*mult)+dish_bonus//3)
        fail=max(0.0,min(.95,(35-self.s.vital)*.018 + max(0,-b[6]-20)*.005)) if t!=4 else 0
        return gain,pt,fail

    def _train(self,t:int):
        gain,pt,fail=self.training_preview(t); cost=TRAIN_BASE[t][6]
        if self.rng.random()<fail:
            self.s.failed_trainings+=1; self.s.vital=max(0,self.s.vital+cost); self.s.motivation=max(1,self.s.motivation-1); return
        self.s.status=[min(2300,a+b) for a,b in zip(self.s.status,gain)]
        self.s.skill_pt+=pt; self.s.vital=max(0,min(self.s.max_vital,self.s.vital+cost))
        for i,p in enumerate(self.s.support_pos):
            if p==t:self.s.bond[i]=min(100,self.s.bond[i]+7)
        mat=t; extra=sum(p==t for p in self.s.support_pos)
        self.s.materials[mat]=min(999,self.s.materials[mat]+20+5*extra)
        self.s.farm_pt+=8+extra

    def _race(self):
        self.s.race_count+=1
        bonus=10 if self.s.turn>=72 else 4
        dish=1.35 if self.s.active_dish else 1.0
        self.s.status=[min(2300,x+int(bonus*dish)) for x in self.s.status]
        self.s.skill_pt+=int((55 if self.forced_race else 40)*dish)
        self.s.vital=max(0,self.s.vital-15)
        mat=self.rng.randrange(5); self.s.materials[mat]=min(999,self.s.materials[mat]+30)

    def _fixed_events(self):
        t=self.s.turn
        if t in (23,35,47,59,71):
            thresholds={23:1000,35:2000,47:5000,59:7000,71:10000}
            win=self.s.dish_pt>=thresholds[t]; add=10 if win else 5
            self.s.status=[min(2300,x+add) for x in self.s.status]; self.s.skill_pt+=50 if win else 35
            self.s.event_counts[0]+=1
        if t in (29,53):
            self.s.status=[min(2300,x+self.rng.randrange(6,18)) for x in self.s.status]
            self.s.event_counts[0]+=1
        if t in (35,59):
            self._auto_upgrade(); self.s.event_counts[0]+=1

    def _generic_event(self):
        if self.s.turn>=72:return
        if self.rng.random()<.28:
            k=self.rng.randrange(5); self.s.status[k]=min(2300,self.s.status[k]+20)
            self.s.skill_pt+=20; self.s.vital=min(self.s.max_vital,self.s.vital+(10 if self.rng.random()<.5 else 0))
            self.s.event_counts[1]+=1
        if self.rng.random()<.04:
            self.s.motivation=max(1,self.s.motivation-1); self.s.event_counts[1]+=1

    def _grass_wonder_event(self):
        """Separate Grass Wonder character-event process.

        Upstream Cook2 approximates all character events statistically. We retain
        that uncertainty but keep it as an explicit character channel with
        Grass-Wonder-oriented speed/power growth instead of generic support events.
        """
        if self.s.turn>=72:return
        scheduled=self.s.turn in (8,20,32,44,56,68)
        if scheduled or self.rng.random()<.045:
            event=self.rng.randrange(4)
            if event==0: self.s.status[0]+=10; self.s.status[2]+=10
            elif event==1: self.s.status[2]+=15; self.s.skill_pt+=15
            elif event==2: self.s.vital=min(self.s.max_vital,self.s.vital+20); self.s.motivation=min(5,self.s.motivation+1)
            else: self.s.status=[x+4 for x in self.s.status]; self.s.skill_pt+=20
            self.s.status=[min(2300,x) for x in self.s.status]; self.s.event_counts[2]+=1

    def _auto_upgrade(self):
        while True:
            choices=[i for i,l in enumerate(self.s.farm_level) if l<5]
            if not choices:return
            i=min(choices,key=lambda z:(self.s.farm_level[z],z)); cost=(100,180,220,250)[self.s.farm_level[i]-1]
            if self.s.farm_pt<cost:return
            self.s.farm_pt-=cost; self.s.farm_level[i]+=1

    def _distribute(self):
        self.s.support_pos=[self.rng.randrange(-1,5) for _ in SUPPORTS]

    def step(self,dish:int,main:int):
        if self.done:raise RuntimeError('finished')
        self.make_dish(dish)
        if main not in self.legal_main():raise ValueError('illegal main action')
        if main<5:self._train(main)
        elif main==5:self.s.vital=min(self.s.max_vital,self.s.vital+self.rng.choice((40,50,60)))
        elif main==6:self.s.vital=min(self.s.max_vital,self.s.vital+20); self.s.motivation=min(5,self.s.motivation+1)
        else:self._race()
        self._fixed_events(); self._generic_event(); self._grass_wonder_event(); self._auto_upgrade()
        self.s.active_dish=0; self.s.turn+=1
        if not self.done:self._distribute()
        self.s.rng_state=self.rng.getstate()

    def score(self):
        # Monotonic proxy used consistently for baselines and final-return labels.
        weighted=sum(min(x,1200)+max(0,x-1200)//2 for x in self.s.status)
        return int(weighted + 2.0*self.s.skill_pt + 8*sum(self.s.bond) - 120*self.s.failed_trainings)

    def features(self):
        x=[]
        x += [self.s.turn/TOTAL_TURNS,self.s.vital/120,self.s.max_vital/120,self.s.motivation/5,self.s.skill_pt/3000,self.s.dish_pt/15000,self.s.farm_pt/1000]
        x += [v/2300 for v in self.s.status]+[v/30 for v in GROWTH]
        x += [v/999 for v in self.s.materials]+[v/5 for v in self.s.farm_level]
        x += [v/100 for v in self.s.bond]
        for p in self.s.support_pos:x += [1.0 if p==i else 0.0 for i in range(-1,5)]
        x += [1.0 if self.forced_race else 0.0]+[self.s.event_counts[i]/20 for i in range(3)]
        for d in range(14):x.append(1.0 if d in self.legal_dishes() else 0.0)
        for a in range(8):x.append(1.0 if a in self.legal_main() else 0.0)
        x += [0.0]*(128-len(x))
        if len(x)!=128:raise AssertionError(len(x))
        return x
