import sys,math,json,random,importlib
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent),str(Path(__file__).resolve().parents[1]/'native')]
from sliced_bond import execute
from bond_contract import execute as unsliced,Boundary
m=importlib.import_module('mps-random-uncompute')
def main():
    n=8;gs=m.make(n,8377)[:120];ref=m.dense(n,gs);r=random.Random(721);count=0;mx=0;max_slices=0
    for v in r.sample(range(1<<n),12):
        b=format(v,f'0{n}b');u=unsliced(n,gs,b,representation='affine',trials=12,plan_only=True);a=execute(n,gs,b,max_bytes=max(4096,int(u['predictedArrayBytes']*.70)),max_slices=1024,trials=12);e=abs(complex(a['real'],a['imag'])-ref[v]);assert e<1e-13,(e,a);count+=1;mx=max(mx,e);max_slices=max(max_slices,a['completedSlices']);assert a['completedSlices']==a['slices']
    assert max_slices>1
    gs=m.make(100,8377);x='0'*100;u=unsliced(100,gs[:600],x,representation='affine',trials=64);a=execute(100,gs[:600],x,max_bytes=max(4096,int(u['predictedArrayBytes']*.7)),max_slices=256,trials=64);e=abs(complex(a['real'],a['imag'])-complex(u['real'],u['imag']));assert e<1e-17,(e,a,u);assert a['completedSlices']>1
    print(json.dumps(dict(smallComparisons=count,maxAbsoluteError=mx,maxSmallSlices=max_slices,depth4=a,depth4Reference=u,depth4AbsoluteError=e),allow_nan=False),flush=True)
if __name__=='__main__':main()
