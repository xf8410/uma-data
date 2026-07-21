"""Cook statistical simulator for fixed 5-star Grass Wonder and real support decks.

Cook turn ordering follows UmaAi Cook2; Cook tables and support-card rows come from
master.mdb snapshots. Random/character/support events remain explicit statistical
approximations, not claims of server-RNG or full event-choice reproduction.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import copy, json, random
from pathlib import Path
from typing import List, Tuple

SCENARIO_ID, TOTAL_TURNS, CARD_ID = 8, 78, 101101
INITIAL_STATUS = (118, 91, 129, 96, 116)
GROWTH = (20, 0, 10, 0, 0)
ROOT = Path(__file__).parent
_MDB = json.loads((ROOT/'cook_mdb_snapshot.json').read_text(encoding='utf-8'))
_CARD_DB = json.loads((ROOT/'support_candidates.json').read_text(encoding='utf-8'))['cards']
_EVENT_PROFILES = json.loads((ROOT/'support_event_profiles.json').read_text(encoding='utf-8'))['profiles']
STATUS_SCORE = tuple(json.loads((ROOT/'five_status_score.json').read_text(encoding='utf-8'))['values'])
_GRASS_TARGETS = tuple(_MDB['grass_wonder_route']['simulator_zero_based_turns'])
TARGET_RACES = frozenset(_GRASS_TARGETS + (73,75,77))
SUCCESS_ODDS = tuple((r['power_min'],r['power_max'],r['success_rate']/100) for r in _MDB['tables']['single_mode_cook_success_odds'])
MEETING_REQUIREMENTS = {r['turn_num']-1:r['success_num'] for r in _MDB['tables']['single_mode_cook_power_data']}
DISH_COST=((0,0,0,0,0),(25,0,50,0,50),(25,50,0,50,0),(150,0,80,0,0),(0,150,0,80,0),(0,80,150,0,0),(40,0,40,150,0),(80,0,0,0,150),(250,0,80,0,0),(0,250,0,80,0),(0,80,250,0,0),(40,0,40,250,0),(80,0,0,0,250),(80,80,80,80,80))
DISH_UNLOCK=(99,0,0,0,0,0,0,0,48,48,48,48,48,72)
DISH_PT=(0,250,250,500,500,500,500,500,800,800,800,800,800,1500)
TRAIN_BASE=((12,0,3,0,0,5,-20),(0,10,0,6,0,5,-21),(0,5,11,0,0,5,-21),(3,0,3,12,0,5,-22),(3,0,0,0,10,7,5))
TYPE_INDEX={'speed':0,'stamina':1,'power':2,'guts':3,'wit':4}
DEFAULT_DECK=(30275,30277,30264,30293,30289,30207)

class Support:
    def __init__(self,row):
        self.id=row['card_id'];self.chara_id=row['chara_id'];self.name=row['title'];self.kind=row['type'];self.train=TYPE_INDEX.get(self.kind,-1)
        self.link=bool(row['is_cook_link']);self.e=dict(row['lv50_effects']);self.u=row.get('unique_effect_raw');self.event=_EVENT_PROFILES.get(str(self.id))
    def effects(self,bond,deck_type_count):
        e=dict(self.e);u=self.u
        if not u:return e
        typ=u['type_0'];v=u['value_0'];a=u['value_0_1'];b=u['value_0_2'];c=u['value_0_3'];d=u['value_0_4']
        names={1:'friendship_bonus',2:'motivation_bonus',3:'speed_bonus',4:'stamina_bonus',5:'power_bonus',6:'guts_bonus',7:'wit_bonus',8:'training_bonus',30:'skill_pt_bonus',33:'hint_count_bonus',41:'all_stat_bonus'}
        def add(t,val):
            n=names.get(t)
            if n:e[n]=e.get(n,0)+val
        if typ==101 and bond>=v:
            add(a,b);add(c,d)
        elif typ==103 and deck_type_count>=v:
            add(8,a)
        elif typ==120 and bond>=a:
            # For each card type in the deck, grant the matching parameter bonus;
            # friend/group cards map to skill points. Each bonus is capped at c.
            counts={k:sum(x.kind==k for x in self._deck_cards) for k in TYPE_INDEX}
            e['composition_bonuses']=[min(c,counts[k]*b) for k in ('speed','stamina','power','guts','wit')]
            e['composition_skill_pt']=min(c,sum(x.kind in ('friend','group') for x in self._deck_cards)*b)
        return e
    @property
    def extra_bond_unique(self):
        u=self.u
        return (u['value_0'],u['value_0_1']) if u and u['type_0']==121 else (0,0)

def validate_deck(ids):
    if len(ids)!=6 or len(set(ids))!=6:raise ValueError('deck must contain six distinct cards')
    cards=[Support(_CARD_DB[str(i)]) for i in ids]
    if len({c.chara_id for c in cards})!=6:raise ValueError('same character cannot be included twice')
    kinds=[c.kind for c in cards]
    if sorted(kinds)!=sorted(['speed','power','guts','guts','wit','friend']):raise ValueError(f'illegal 1/1/2/1/1 deck: {kinds}')
    if 30207 not in ids:raise ValueError('director support 30207 is mandatory')
    for card in cards:card._deck_cards=cards
    return cards

@dataclass
class State:
    seed:int;turn:int=0;status:List[int]=field(default_factory=lambda:list(INITIAL_STATUS));skill_pt:int=0
    vital:int=100;max_vital:int=100;motivation:int=3;materials:List[int]=field(default_factory=lambda:[0]*5)
    farm_level:List[int]=field(default_factory=lambda:[1]*5);farm_pt:int=0;dish_pt:int=0;active_dish:int=0
    bond:List[int]=field(default_factory=lambda:[0]*6);support_pos:List[int]=field(default_factory=lambda:[-1]*6)
    npc_pos:List[int]=field(default_factory=list);event_counts:List[int]=field(default_factory=lambda:[0,0,0,0])
    race_count:int=0;failed_trainings:int=0;hint_skills:int=0;director_npc_present:bool=True
    friend_stage:int=0;friend_outings:int=0;refresh_mind:bool=False
    support_chain_done:List[int]=field(default_factory=lambda:[0]*6);rng_state:object=None

class CookSimulator:
    def __init__(self,seed:int,deck_ids=DEFAULT_DECK):
        self.rng=random.Random(seed);self.cards=validate_deck(tuple(deck_ids));self.deck_ids=tuple(deck_ids)
        for card in self.cards:card._deck_cards=self.cards
        self.deck_type_count=len({c.kind for c in self.cards});self.s=State(seed=seed)
        self.s.bond=[c.e.get('initial_bond',0) for c in self.cards]
        for c in self.cards:
            for i,n in enumerate(('initial_speed','initial_stamina','initial_power','initial_guts','initial_wit')):self.s.status[i]+=c.e.get(n,0)
            self.s.skill_pt+=c.e.get('initial_skill_pt',0)
        # Carrying director support suppresses non-card director; Cook2 replaces it with one more generic NPC.
        self.s.director_npc_present=not any(c.chara_id==9002 for c in self.cards)
        self._distribute();self.s.rng_state=self.rng.getstate()
    def clone(self):x=copy.deepcopy(self);x.rng=random.Random();x.rng.setstate(self.rng.getstate());return x
    @property
    def forced_race(self):return self.s.turn in TARGET_RACES
    @property
    def done(self):return self.s.turn>=TOTAL_TURNS
    def legal_dishes(self):
        out=[0]
        if self.s.active_dish:return out
        for d in range(1,14):
            if self.s.turn<DISH_UNLOCK[d]:continue
            cost=[100]*5 if d==13 and self.s.dish_pt<10000 else DISH_COST[d]
            if all(a>=b for a,b in zip(self.s.materials,cost)):out.append(d)
        return out
    def legal_main(self):
        if self.forced_race:return [7]
        return sorted(set([5,6,7]+[t for t in range(5) if self.s.vital>8 or t==4]))
    def make_dish(self,d):
        if d not in self.legal_dishes():raise ValueError('illegal dish')
        if not d:return
        cost=[100]*5 if d==13 and self.s.dish_pt<10000 else DISH_COST[d]
        self.s.materials=[a-b for a,b in zip(self.s.materials,cost)];self.s.dish_pt+=DISH_PT[d];self.s.active_dish=d
        rate=next(rate for lo,hi,rate in SUCCESS_ODDS if lo<=self.s.dish_pt<=hi)
        if self.rng.random()<rate:self.s.vital=min(self.s.max_vital,self.s.vital+10);self.s.motivation=min(5,self.s.motivation+1)
    def _people(self,t):return [i for i,p in enumerate(self.s.support_pos) if p==t]
    def training_preview(self,t)->Tuple[List[int],int,float]:
        b=TRAIN_BASE[t];people=self._people(t);npc=sum(p==t for p in self.s.npc_pos);head=len(people)+npc
        base=list(b[:6]);total_training=total_mood=0;friend_mult=1.;vital_drop=fail_drop=0
        for i in people:
            c=self.cards[i];e=c.effects(self.s.bond[i],self.deck_type_count)
            for j,n in enumerate(('speed_bonus','stamina_bonus','power_bonus','guts_bonus','wit_bonus','skill_pt_bonus')):
                if base[j]>0:base[j]+=e.get(n,0)
            allb=e.get('all_stat_bonus',0)
            if allb:
                for j in range(5):
                    if base[j]>0:base[j]+=allb
            if e.get('composition_bonuses'):
                for j,val in enumerate(e['composition_bonuses']):
                    if base[j]>0:base[j]+=val
                if base[5]>0:base[5]+=e.get('composition_skill_pt',0)
            total_training+=e.get('training_bonus',0);total_mood+=e.get('motivation_bonus',0)
            if c.train==t and self.s.bond[i]>=80:friend_mult*=1+e.get('friendship_bonus',0)/100
            vital_drop=1-(1-vital_drop)*(1-e.get('vital_cost_drop',0)/100);fail_drop=1-(1-fail_drop)*(1-e.get('failure_rate_drop',0)/100)
        mood=1+0.1*(self.s.motivation-3)*(1+total_mood/100)
        mult=(1+.05*head)*(1+total_training/100)*mood*friend_mult
        dish=0
        if self.s.active_dish:
            main=(self.s.active_dish-3)%5 if 3<=self.s.active_dish<=12 else -1;dish=8+(12 if main==t else 0)+(8 if self.s.active_dish==13 else 0)
        gain=[max(0,int(v*mult*(1+GROWTH[i]/100)+(dish if v else 0))) for i,v in enumerate(base[:5])]
        pt=max(0,int(base[5]*mult)+dish//3);cost=int(b[6]*(1-vital_drop))
        fail=(max(0,(35-self.s.vital)*.018+max(0,-cost-20)*.005)*(1-fail_drop)) if t!=4 else 0
        return gain,pt,min(.95,fail)
    def _hint(self,t):
        hs=[]
        for i in self._people(t):
            c=self.cards[i];e=c.effects(self.s.bond[i],self.deck_type_count)
            if self.rng.random()<.06*(1+e.get('hint_rate',0)/100):hs.append((i,e))
        if not hs:return
        i,e=self.rng.choice(hs);count=1+e.get('hint_count_bonus',0);level=max(1,e.get('hint_level',0))
        self.s.hint_skills+=count;self.s.skill_pt+=int(count*level*6.5);self.s.bond[i]=min(100,self.s.bond[i]+5)
    def _train(self,t):
        gain,pt,fail=self.training_preview(t);cost=TRAIN_BASE[t][6]
        if self.rng.random()<fail:self.s.failed_trainings+=1;self.s.vital=max(0,self.s.vital+cost);self.s.motivation=max(1,self.s.motivation-1);return
        self.s.status=[min(2800,a+b) for a,b in zip(self.s.status,gain)];self.s.skill_pt+=pt
        vital_drop=0
        for i in self._people(t):
            drop=self.cards[i].effects(self.s.bond[i],self.deck_type_count).get('vital_cost_drop',0)/100
            vital_drop=1-(1-vital_drop)*(1-drop)
        real_cost=int(cost*(1-vital_drop)) if cost<0 else cost
        self.s.vital=max(0,min(self.s.max_vital,self.s.vital+real_cost))
        friend_idx=next(i for i,c in enumerate(self.cards) if c.kind=='friend');friend_together=friend_idx in self._people(t)
        for i,c in enumerate(self.cards):
            together=self.s.support_pos[i]==t;extra=c.extra_bond_unique[1 if together else 0]
            if together:
                base=7 if c.kind=='friend' else 8+(2 if friend_together else 0)
                self.s.bond[i]=min(100,self.s.bond[i]+base+extra)
            elif extra:self.s.bond[i]=min(100,self.s.bond[i]+extra)
        self._hint(t)
        friend_idx=next(i for i,c in enumerate(self.cards) if c.kind=='friend')
        if friend_idx in self._people(t):self._friend_click(friend_idx)
        extra=len(self._people(t))+sum(p==t for p in self.s.npc_pos)+2*sum(self.cards[i].link for i in self._people(t))
        self.s.materials[t]=min(999,self.s.materials[t]+20+5*extra);self.s.farm_pt+=8+extra
    def _friend_click(self,i):
        recovery=1+self.cards[i].e.get('event_recovery',0)/100
        if self.s.friend_stage==0:
            self.s.friend_stage=1;self.s.status[0]+=14;self.s.bond[i]=min(100,self.s.bond[i]+10);self.s.motivation=min(5,self.s.motivation+1)
        elif self.rng.random()>=.6:
            if self.s.turn<24:
                others=[j for j,c in enumerate(self.cards) if c.kind!='friend'];j=min(others,key=lambda z:self.s.bond[z]);self.s.bond[j]=min(100,self.s.bond[j]+3)
            elif self.s.turn<48:self.s.status[0]+=12
            else:self.s.status[3]+=12
            self.s.bond[i]=min(100,self.s.bond[i]+5)
        if self.s.friend_stage==1:
            prob=.35 if self.s.bond[i]>=60 else .15
            if self.rng.random()<prob:
                self.s.friend_stage=2;self.s.vital=min(self.s.max_vital,self.s.vital+int(25*recovery));self.s.motivation=min(5,self.s.motivation+1)
    def _friend_outing(self):
        i=next(i for i,c in enumerate(self.cards) if c.kind=='friend');recovery=1+self.cards[i].e.get('event_recovery',0)/100;k=self.s.friend_outings
        vit=(30,30,43,30,30)[k];guts=(20,10,0,25,36)[k];speed=(0,10,0,0,0)[k]
        if k==2 and self.s.max_vital-self.s.vital<20:guts=29;vit=0
        if k==4 and self.rng.random()<.25:vit,guts=(26,24);self.s.skill_pt+=40
        elif k==4:self.s.skill_pt+=72
        self.s.vital=min(self.s.max_vital,self.s.vital+int(vit*recovery));self.s.status[0]+=speed;self.s.status[3]+=guts;self.s.motivation=min(5,self.s.motivation+1);self.s.bond[i]=min(100,self.s.bond[i]+5);self.s.materials=[min(999,x+40) for x in self.s.materials];self.s.friend_outings+=1;self.s.refresh_mind=True
    def _race(self):
        self.s.race_count+=1;bonus=10 if self.s.turn>=72 else 4;dish=1.35 if self.s.active_dish else 1
        rb=1+sum(c.e.get('race_bonus',0) for c in self.cards)/100
        self.s.status=[min(2800,x+int(bonus*dish*rb)) for x in self.s.status];self.s.skill_pt+=int((55 if self.forced_race else 40)*dish*rb);self.s.vital=max(0,self.s.vital-15)
        m=self.rng.randrange(5);self.s.materials[m]=min(999,self.s.materials[m]+30)
    def _fixed_events(self):
        t=self.s.turn
        if self.s.refresh_mind:
            self.s.vital=min(self.s.max_vital,self.s.vital+5)
            if self.rng.random()<.25:self.s.refresh_mind=False
        if t in MEETING_REQUIREMENTS:
            win=self.s.dish_pt>=MEETING_REQUIREMENTS[t];add=10 if win else 5;self.s.status=[min(2800,x+add) for x in self.s.status];self.s.skill_pt+=50 if win else 35;self.s.event_counts[0]+=1
        if t in (29,53):self.s.status=[min(2800,x+self.rng.randrange(6,18)) for x in self.s.status];self.s.event_counts[0]+=1
        if t in (35,59):self._auto_upgrade();self.s.event_counts[0]+=1
    def _apply_event_gain(self,e):
        for i,k in enumerate(('speed','stamina','power','guts','wit')):self.s.status[i]=min(2800,self.s.status[i]+int(e.get(k,0)))
        self.s.skill_pt+=int(e.get('skill_pt',0)+6.5*e.get('skill_levels',0));self.s.vital=min(self.s.max_vital,self.s.vital+int(e.get('vital',0)));self.s.motivation=min(5,self.s.motivation+int(e.get('motivation',0)))
    def _support_chain_event(self):
        available=[i for i,c in enumerate(self.cards) if c.event and self.s.support_chain_done[i]<c.event['chain_event_count']]
        if not available or self.rng.random()>=.18:return
        i=self.rng.choice(available);p=self.cards[i].event;n=max(1,p['chain_event_count']);gain={k:v/n for k,v in p['chain_optimal_total'].items()};self._apply_event_gain(gain);self.s.bond[i]=min(100,self.s.bond[i]+int(gain.get('bond',0)));self.s.support_chain_done[i]+=1;self.s.event_counts[3]+=1
    def _events(self):
        if self.s.turn>=72:return
        if self.rng.random()<.28:
            k=self.rng.randrange(5);self.s.status[k]=min(2800,self.s.status[k]+20);self.s.skill_pt+=20;self.s.event_counts[1]+=1
        if self.s.turn in (8,20,32,44,56,68) or self.rng.random()<.045:
            k=self.rng.randrange(4)
            if k==0:self.s.status[0]+=10;self.s.status[2]+=10
            elif k==1:self.s.status[2]+=15;self.s.skill_pt+=15
            elif k==2:self.s.vital=min(self.s.max_vital,self.s.vital+20);self.s.motivation=min(5,self.s.motivation+1)
            else:self.s.status=[x+4 for x in self.s.status];self.s.skill_pt+=20
            self.s.status=[min(2800,x) for x in self.s.status];self.s.event_counts[2]+=1
        if self.rng.random()<.28:
            c=self.rng.randrange(6);card=self.cards[c];profile=card.event
            if profile:
                # Random support events use candidate-specific unpacked averages.
                e=profile['random_event_optimal_mean'];self._apply_event_gain(e);self.s.bond[c]=min(100,self.s.bond[c]+int(e.get('bond',0)))
            else:
                self.s.bond[c]=min(100,self.s.bond[c]+5);self.s.skill_pt+=15;self.s.vital=min(self.s.max_vital,self.s.vital+8)
            self.s.event_counts[3]+=1
        self._support_chain_event()
    def _auto_upgrade(self):
        while True:
            q=[i for i,l in enumerate(self.s.farm_level) if l<5]
            if not q:return
            i=min(q,key=lambda z:(self.s.farm_level[z],z));cost=(100,180,220,250)[self.s.farm_level[i]-1]
            if self.s.farm_pt<cost:return
            self.s.farm_pt-=cost;self.s.farm_level[i]+=1
    def _distribute(self):
        pos=[]
        for c in self.cards:
            w=[100]*5+[100 if c.kind=='friend' else 50]
            if c.train>=0:w[c.train]+=c.e.get('specialty_rate',0)
            pos.append(self.rng.choices(range(-1,5),weights=[w[5]]+w[:5])[0])
        self.s.support_pos=pos
        # Cook2: friend deck has no non-card director and seven generic NPCs instead of six.
        n=7 if not self.s.director_npc_present else 6;self.s.npc_pos=[self.rng.randrange(-1,5) for _ in range(n)]
    def step(self,dish,main):
        if self.done:raise RuntimeError('finished')
        self.make_dish(dish)
        if main not in self.legal_main():raise ValueError('illegal main action')
        if main<5:self._train(main)
        elif main==5:self.s.vital=min(self.s.max_vital,self.s.vital+self.rng.choice((40,50,60)))
        elif main==6:
            if self.s.friend_stage>=2 and self.s.friend_outings<5:self._friend_outing()
            else:self.s.vital=min(self.s.max_vital,self.s.vital+20);self.s.motivation=min(5,self.s.motivation+1)
        else:self._race()
        self._fixed_events();self._events();self._auto_upgrade();self.s.active_dish=0;self.s.turn+=1
        if not self.done:self._distribute()
        self.s.rng_state=self.rng.getstate()
    def score(self):
        return sum(STATUS_SCORE[min(2800,max(0,x))] for x in self.s.status)+2*self.s.skill_pt+510
    def features(self):
        x=[self.s.turn/TOTAL_TURNS,self.s.vital/120,self.s.max_vital/120,self.s.motivation/5,self.s.skill_pt/5000,self.s.dish_pt/15000,self.s.farm_pt/1000]
        x += [v/2800 for v in self.s.status]+[v/30 for v in GROWTH]+[v/999 for v in self.s.materials]+[v/5 for v in self.s.farm_level]+[v/100 for v in self.s.bond]
        for p in self.s.support_pos:x += [1. if p==i else 0. for i in range(-1,5)]
        x += [1. if self.forced_race else 0.]+[v/20 for v in self.s.event_counts]
        x += [1. if d in self.legal_dishes() else 0. for d in range(14)]+[1. if a in self.legal_main() else 0. for a in range(8)]
        x += [0.]*(128-len(x))
        if len(x)!=128:raise AssertionError(len(x))
        return x
