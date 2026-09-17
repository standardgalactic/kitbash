"""Independent reproduction of every worked number in the book.
Run: python3 verify.py   (needs numpy). Exits nonzero on any failed assertion."""
import itertools, math
import numpy as np

# ---- Ch3: edit counts
assert math.comb(95,3)==138415 and 138415*24==3321960 and 3*2**3==24
assert math.comb(20,10)==184756
assert round(14/96,3)==0.146 and round(4/96,3)==0.042 and round((14/96)/(4/96),1)==3.5

# ---- Ch14: response model
def r(p):
    p1,p2,p3,p4=p
    return np.array([np.tanh((p1+0.5*p4)/6),
                     1/(1+np.exp(-(p3+5)/4))*np.exp(-(p2-2)**2/18),
                     1-np.exp(-p4/2)])
def jac(p,h=1e-6):
    J=np.zeros((3,4))
    for i in range(4):
        e=np.zeros(4); e[i]=h
        J[:,i]=(r(p+e)-r(p-e))/(2*h)
    return J
b=np.array([7,2,-2,4.])
assert np.allclose(r(b),[0.9051,0.6792,0.8647],atol=5e-5)
J=jac(b); D=np.diag([1,1,2,1.])          # budget: 1 s, 1 s, 2 dB, 1 s ; W = I ; rho = 1
s=np.linalg.svd(J@D)[1]
assert np.allclose(s,[0.1089,0.0697,0.0292],atol=5e-5)
deff=lambda eps,rho=1:int((s>eps/rho).sum())
assert deff(0.05)==2 and deff(0.02)==3
Wh=np.diag([2,1,1.]); sw=np.linalg.svd(Wh@J@D)[1]
print("weighted W=diag(4,1,1) singular values",np.round(sw,4))
# remainder bound along the p2 line: restrict to t -> r(b + t e2); directional second derivative
f=lambda t:r(b+np.array([0,t,0,0]))[1]
def d2(g,t,h=1e-4): return (g(t+h)-2*g(t)+g(t-h))/h**2
M2=max(abs(d2(f,t)) for t in np.linspace(0,3,301))
print("M along p2 line on [0,3]:",M2)
for h in (1.5,3.0):
    err=abs(f(h)-f(0)-0)   # first-order prediction is 0
    assert err<=0.5*M2*h*h+1e-9
    print("p2 shift",h,"change",f(h)-f(0),"bound",0.5*M2*h*h)
print("radius sqrt(2 eps/M):",math.sqrt(2*0.05/M2))
# p1 line
g=lambda t:r(b+np.array([t,0,0,0]))[0]
for h in (-4.0,-1.35,2.32):
    ts=np.linspace(min(0,h),max(0,h),401)
    M1=max(abs(d2(g,t)) for t in ts)
    err=abs(g(h)-g(0)-jac(b)[0,0]*h)
    assert err<=0.5*M1*h*h+1e-9
    print("p1 shift",h,"actual",g(h)-g(0),"linear",jac(b)[0,0]*h,"remainder",err,"bound",0.5*M1*h*h)
lo=6*math.atanh(r(b)[0]-0.05)-2; hi=6*math.atanh(r(b)[0]+0.05)-2
assert abs(7-lo-1.35)<0.005 and abs(hi-7-2.32)<0.005

# ---- Ch15: sound
D0,mu,floor=60,3,50
def levels(att=lambda name:0):
    L={}
    for t in range(96): L[t]=('ambient',40)
    for t in (20,21,22): L[t]=('street',64)
    L[52]=('buzz',54)
    for t in (78,79): L[t]=('door',72)
    for k in range(16): L[80+k]=('music',58+0.8*k)
    return {t:(n,l-att(n)) for t,(n,l) in L.items()}
def occ(att):
    lv=levels(att); E=[t for t in range(96) if lv[t][1]>D0+mu+1e-9]
    blocks=[];
    for t in E:
        if blocks and blocks[-1][1]==t-1: blocks[-1][1]=t
        else: blocks.append([t,t])
    rec=[blocks[i+1][0]-blocks[i][1]-1 for i in range(len(blocks)-1)]
    return len(E),blocks,rec,lv[52][1]
for a,exp in ((0,(14,3,[55,7],54)),(4,(6,2,[12],50)),(6,(4,2,[14],48))):
    n,bl,rec,buzz=occ(lambda nm,a=a:a)
    assert (n,len(bl),rec,buzz)==exp,(a,n,bl,rec,buzz)
amax=min(72-floor,54-floor); assert amax==4
good=[a for a in np.arange(0,12,0.01) if occ(lambda nm,a=a:a)[0]==4]
print("a with 4 exceeding steps:",round(min(good),2),round(max(good),2))
S=lambda nm:{'street':1,'music':7}.get(nm,0)
n,bl,rec,_=occ(S); assert n==2 and bl==[[78,79]]
Sx=lambda nm:{'street':1,'music':7,'door':9}.get(nm,0)
assert occ(Sx)[0]==0
assert 12<=D0+mu-floor==13      # music range 70-58
assert 70-63==7 and 58-50==8

# ---- Ch16: command semantics by simulation (not assumed from a chain)
def run(seq):
    st=set()
    for c in seq:
        if c=='skl': st.add('KA')
        elif c=='skc':
            if 'KA' not in st or 'KB' in st: return False
            st.add('conceal')
        elif c=='skr':
            if 'conceal' not in st: return False
            st.add('KB')
        elif c=='grb':
            if 'KB' not in st: return False
            st.add('react')
        elif c=='sdx':
            if 'react' not in st: return False   # as in the revised table
        elif c=='smq': pass
    return True
cmds=['skl','skc','skr','grb','sdx','smq']
valid=[p for p in itertools.permutations(cmds) if run(p)]
print("valid orderings (sdx requires reaction):",len(valid))
def run2(seq):                    # sdx requires only Knows(B)
    st=set()
    for c in seq:
        if c=='skl': st.add('KA')
        elif c=='skc':
            if 'KA' not in st or 'KB' in st: return False
            st.add('conceal')
        elif c=='skr':
            if 'conceal' not in st: return False
            st.add('KB')
        elif c in('grb','sdx'):
            if 'KB' not in st: return False
    return True
print("valid orderings (sdx requires only Knows(B)):",sum(run2(p) for p in itertools.permutations(cmds)))
# realizations
real=[(df,d,sl) for df in('spoken','gesture') for d in(2,3,4,5,6) for sl in('hard','soft')]
adm=[x for x in real if not(x[2]=='soft' and x[1]<4)]
assert len(real)==20 and len(adm)==16

# ---- Ch17: real passage, Drive Through Fire (values transcribed from Tables 7.3-7.5 of the monograph)
def sec(h,m,s): return 3600*h+60*m+s
blocks=[((0,8,18),(0,9,30),7.0,17.0,0),((0,20,11),(0,21,13),8.2,18.2,14),((0,36,23),(0,38,14),7.5,17.5,3),
        ((1,0,48),(1,2,29),9.1,19.1,10),((1,4,24),(1,5,56),10.7,20.7,0),((1,6,46),(1,8,5),12.8,22.8,10),
        ((1,9,24),(1,11,34),6.5,16.5,48),((1,13,45),(1,14,58),8.8,18.8,13),((1,15,9),(1,19,53),10.4,20.4,30)]
dur=[sec(*e)-sec(*b) for b,e,_,_,_ in blocks]
assert abs(sum(dur)/60-16.7)<0.05 and max(dur)==284 and abs(max(dur)/60-4.7)<0.05
thr=[t for *_,t,q,_ in blocks]; assert all(abs((q-10)-t)<1e-9 for _,_,t,q,_ in blocks)
assert sorted(thr)[4]==8.8 and max(thr)==12.8
assert sum(x[4] for x in blocks)==128 and round(100*128/1499,1)==8.5
assert sec(1,15,9)-sec(1,14,58)==11 and sec(1,19,53)-sec(1,13,45)==368
last6=sum(dur[3:]); span=sec(1,20,51)-sec(1,0,39)
assert last6==759 and span==1212 and round(100*last6/span,1)==62.6
gaps=[((1,0,39),(1,3,18)),((1,3,27),(1,9,0)),((1,9,21),(1,20,51))]
rw=[sec(*gaps[1][0])-sec(*gaps[0][1]), sec(*gaps[2][0])-sec(*gaps[1][1])]
assert rw==[9,21] and sum(rw)==30   # connecting intervals; qualifying windows are 9+7+13=29 (see real_passage.py)
assert sum(sec(*e)-sec(*b) for b,e in gaps)+30==span
assert round(100*1598 and 926/1598*100,1)==57.9 and round(1499/5222*100,1)==28.7 and round(34.6+0 ,1)==34.6
print("share subtitled by block:",[round(100*x[4]/d,1) for x,d in zip(blocks,dur)])
print("0.11 dB:",round(10*math.log10(1+10**(-1.6)),3))
print("all checks passed")
