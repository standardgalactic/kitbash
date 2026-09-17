"""Recomputes the Drive Through Fire passage analysis of Chapter 17 from the per-second table
(data/seconds.csv, data/occupation.json; copied from standardgalactic/kitbash, audio-analysis/results).
Run: python3 real_passage.py   (needs numpy, pandas). Exits nonzero on a failed assertion."""
import json, numpy as np, pandas as pd
d=pd.read_csv('data/seconds.csv'); oc=json.load(open('data/occupation.json'))
idx=np.arange(len(d)); P0,P1=3639,4851            # 1:00:39 to 1:20:51
inpass=(idx>=P0)&(idx<P1)
occ=d.occupied.values.astype(bool); inb=d.in_block.values.astype(bool); sub=d.dialogue_sub.values.astype(bool)
x=d.center_adv.values; rel=d.rel_db.values

# 1. reproduce occupation blocks from the occupied seconds (g=5 s merge, m=60 s)
def blocks(g,m=60):
    runs=[];i=0;n=len(occ)
    while i<n:
        if occ[i]:
            j=i
            while j+1<n and occ[j+1]: j+=1
            runs.append([i,j]); i=j+1
        else: i+=1
    out=[]
    for r in runs:
        if out and r[0]-out[-1][1]-1<=g: out[-1][1]=r[1]
        else: out.append(list(r))
    return [(a,b+1) for a,b in out if b-a+1>=m]
b5=blocks(5)
tab=[(int(b['start']),int(b['end'])) for b in oc['occupation_blocks']]
assert b5==tab and len(b5)==9
inpassage=lambda bl:[b for b in bl if b[0]>=P0 and b[1]<=P1]
counts={g:len(inpassage(blocks(g))) for g in (5,10,11,12)}
print("blocks inside the passage by merge gap:",counts)
assert counts[5]==6 and counts[10]==5 and counts[11]==4
assert (4425,4793) in blocks(11) and 4793-4425==368

# 2. passage totals
assert (occ&inpass).sum()==817 and (inb&inpass).sum()==759 and inpass.sum()==1212
assert round(100*759/1212,1)==62.6

# 3. throttle depth and what global gain leaves
for b in oc['occupation_blocks']:
    s,e,t=int(b['start']),int(b['end']),b['implied_throttle_db']
    left=((rel[s:e]-t)>=10).sum()
    assert left/(e-s)<=0.07
    
# 4. centre advantage of subtitled speech
q=lambda v:np.round(np.percentile(v,[10,25,50,75,90]),1)
print("speech in blocks:",q(x[sub&inb]),"outside:",q(x[sub&~inb]),"all:",q(x[sub]))
assert np.isclose(np.median(x[sub&inb]),8.8,atol=0.05) and np.isclose(np.median(x[sub&~inb]),17.0,atol=0.05)
assert np.isclose(np.median(x[sub]),16.0,atol=0.05)

# 5. idealised non-centre attenuation: mix power = centre + non-centre; non-centre scaled by -a dB
def dL(a):
    r=10**(x/10)
    return 10*np.log10((r+(0 if np.isinf(a) else 10**(-a/10)))/(r+1))
print("passage occupied seconds:",(occ&inpass).sum())
for a in (6,12,20,np.inf):
    new=(rel+dL(a)>=10)
    print("a=%s: occupied left in passage %d, in blocks %d of 759; speech-in-blocks mix change median %.2f dB, 10th pct %.2f dB"%(
        a,(new&inpass&occ).sum(),(new&inpass&inb).sum(),np.median(dL(a)[sub&inb]),np.percentile(dL(a)[sub&inb],10)))
assert (((rel+dL(np.inf))>=10)&inpass&inb).sum()==435
assert (((rel+dL(12))>=10)&inpass&inb).sum()==480
print("rms_db minus power sum of centre and non-centre, median over audible seconds: %.2f dB"%np.median((d.rms_db-10*np.log10(10**(d.center_db/10)+10**(d.noncenter_db/10)))[d.audible]))
print("share of occupied passage seconds with centre advantage < 0: %.1f%%"%(100*(x[occ&inpass]<0).mean()))

# 6. recovery windows computed directly from the mask (>=5 s at or below D, or inaudible)
low=((d.rel_db<=0)|(~d.audible)).values
def runs_of(mask):
    out=[];i=0
    while i<len(mask):
        if mask[i]:
            j=i
            while j+1<len(mask) and mask[j+1]: j+=1
            out.append((i,j+1)); i=j+1
        else: i+=1
    return out
win=[r for r in runs_of(low) if r[1]-r[0]>=5]
assert len(win)==105 and sum(b-a for a,b in win)==1526
pw=[(a,b) for a,b in win if a>=P0 and b<=P1]
assert [b-a for a,b in pw]==[9,7,13] and sum(b-a for a,b in pw)==29
assert pw[2][0]-pw[1][1]==1
q=runs_of((d.rel_db.values<=0)&inpass)
assert sum(b-a for a,b in q)==80 and len(q)==32 and max(b-a for a,b in q)==13

# 7. the 130 s excerpt 1:09:24-1:11:34 (seconds 4164..4293), with subtitle-cue timings (data/cues_1h09_1h11.csv)
Q0,Q1=4164,4294
inq=(idx>=Q0)&(idx<Q1)
E=d.level_db.values-(-34.6)
assert inq.sum()==130 and occ[inq].sum()==106 and inb[inq].all() and sub[inq].sum()==48
assert (E[inq]>0).all() and abs(np.median(E[inq])-12.57)<0.01 and abs(E[inq].min()-5.32)<0.01
assert abs(np.median(x[inq&sub])-9.30)<0.01 and abs(np.median(x[inq&~sub])+4.84)<0.01 and (x[inq&sub]<0).sum()==3
cues=pd.read_csv('data/cues_1h09_1h11.csv')
# the flag is "cue covers at least half of the second"; the cue file is timings only (no text)
assert (d.sub_coverage.values[inq&sub]>=0.5).all() and (d.sub_coverage.values[inq&~sub]<0.5).all()
g=runs_of(~sub&inq)
print("longest subtitle-free stretch in excerpt: %d s from offset %d"%(max(b-a for a,b in g),max(g,key=lambda r:r[1]-r[0])[0]-Q0))
for i in range(0,130,10):
    m=(idx>=Q0+i)&(idx<Q0+i+10)
    print(i,int(occ[m].sum()),int(sub[m].sum()),round(float(np.median(E[m])),1),round(float(np.median(x[m])),1))
print("all checks passed")
