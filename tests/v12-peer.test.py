#!/usr/bin/env python3
"""Local 20-case format rehearsal, not a blind independent test.
Generates references separately using analytical QFT/GHZ or local mpmath
state scatter. Repeats on two clean source copies, not separate physical hosts.
"""
import argparse, hashlib, json, pathlib, random, shutil, subprocess, sys, tempfile
import mpmath as mp
ROOT=pathlib.Path(__file__).resolve().parents[1];mp.mp.dps=100

def gate(name,q,controls=(),**kw):return {'name':name,'q':q,'controls':list(controls),**kw}
def pair_case(n,rng,family):
    ids=list(range(n));rng.shuffle(ids);gs=[];factors=[]
    def apply(a,q,M,c=None):
        b=[mp.mpc(0)]*4
        for x in range(4):
            if c is not None and not (x>>c&1):b[x]+=a[x];continue
            col=x>>q&1
            for row in range(2):b[(x&~(1<<q))|(row<<q)]+=M[2*row+col]*a[x]
        return b
    def rot(t,axis):
        c,s=mp.cos(mp.mpf(t)/2),mp.sin(mp.mpf(t)/2)
        return [c,-s,s,c] if axis=='ry' else [c,-mp.j*s,-mp.j*s,c] if axis=='rx' else [mp.exp(-mp.j*mp.mpf(t)/2),0,0,mp.exp(mp.j*mp.mpf(t)/2)]
    for j in range(0,n,2):
        pair=ids[j:j+2];a=[mp.mpc(1),mp.mpc(0),mp.mpc(0),mp.mpc(0)]
        def single(name,k,t=None):
            nonlocal a
            M=[1/mp.sqrt(2),1/mp.sqrt(2),1/mp.sqrt(2),-1/mp.sqrt(2)] if name=='h' else rot(t,name);gs.append(gate(name,pair[k],**({} if t is None else {'theta':t})));a=apply(a,k,M)
        def cx():
            nonlocal a
            gs.append(gate('cx',pair[1],[pair[0]]));a=apply(a,1,[0,1,1,0],0)
        if family=='RCS':
            for layer in range(5):
                for k in range(2):single(rng.choice(['rx','ry','rz']),k,rng.uniform(-2.1,2.1))
                cx()
        else:
            for k in range(2):single('h',k)
            for layer in range(3):
                gamma=rng.uniform(-1.5,1.5);beta=rng.uniform(-1.5,1.5);cx();single('rz',1,gamma);cx();single('rx',0,beta);single('rx',1,beta)
        factors.append((pair,a))
    bits=''.join(rng.choice('01') for _ in range(n));amp=mp.mpc(1)
    for pair,a in factors:amp*=a[sum(int(bits[n-1-q])<<k for k,q in enumerate(pair))]
    pair,a=factors[0];p=['I']*n
    for q in pair:p[n-1-q]='Z'
    ev=sum(abs(v)**2*(-1)**((x&1)+(x>>1)) for x,v in enumerate(a));return gs,[('amplitude',bits,amp),('pauli',''.join(p),ev),('norm',None,mp.mpf(1))]
def fixture():
    rng=random.Random(76399113);cs=[];refs={}
    def add(n,family,gs,items,mid=None):
        ident=f'{family.lower()}-{n}';queries=[];expected={}
        for i,(kind,arg,v,prefix) in enumerate(items):
            q={'id':f'q{i}','kind':kind,'prefix':prefix};q.update({'bits':arg} if kind=='amplitude' else {'pauli':arg} if kind=='pauli' else {});queries.append(q);t={'real':float(mp.re(v)),'imag':float(mp.im(v)),'absoluteTolerance':1e-13};
            if kind=='amplitude' and abs(v)>0:t['relativeTolerance']=1e-9
            expected[q['id']]=t
        cs.append({'id':ident,'family':family,'request':{'n':n,'gates':gs,'queries':queries,'method':'adaptive','requireCertificate':False,'checkpointEvery':100000,'maxBytes':67108864,'maxWork':100000000}});refs[ident]=expected
    for n in [50,60,70,80,100]:
        x=rng.randrange(1,2**n);gs=[gate('x',q) for q in range(n) if x>>q&1]
        for q in range(n-1,-1,-1):
            gs.append(gate('h',q))
            for c in range(q-1,-1,-1):gs.append(gate('cp',q,[c],theta=float(mp.pi/(2**(q-c))),piTheta=['1',str(2**(q-c))]))
        for q in range(n//2):gs.append(gate('swap',n-1-q,[q]))
        items=[]
        for _ in range(3):
            y=rng.randrange(2**n);amp=mp.exp(2*mp.j*mp.pi*((x*y)%(2**n))/(2**n))*mp.power(2,-mp.mpf(n)/2);items.append(('amplitude',format(y,f'0{n}b'),amp,len(gs)))
        items.append(('norm',None,mp.mpf(1),len(gs)));add(n,'QFT',gs,items)
        for family in ['RCS','QAOA']:
            gs,items=pair_case(n,rng,family);add(n,family,gs,[(a,b,c,len(gs)) for a,b,c in items])
        # Actual connected GHZ entangle, non-Clifford phase, reverse all gates.
        phase=rng.uniform(-1,1);gs=[gate('h',0)]+[gate('cx',q,[q-1]) for q in range(1,n)]+[gate('rz',n-1,theta=phase)];mid=len(gs);inverse=[dict(g,theta=-g['theta']) if 'theta' in g else dict(g) for g in reversed(gs)];gs+=inverse
        amp=mp.exp(-mp.j*mp.mpf(phase)/2)/mp.sqrt(2);add(n,'UNCOMPUTE',gs,[('amplitude','0'*n,amp,mid),('amplitude','0'*n,mp.mpf(1),len(gs)),('amplitude','1'*n,mp.mpf(0),len(gs)),('norm',None,mp.mpf(1),len(gs))])
    return {'schema':'DSIQ-blind-challenge-v1','suiteId':'LOCAL-REHEARSAL-NOT-INDEPENDENT','circuits':cs},{'schema':'DSIQ-blind-reference-v1','suiteId':'LOCAL-REHEARSAL-NOT-INDEPENDENT','referenceMethod':'LOCAL ONLY: 100-digit mpmath analytical QFT/GHZ and independent two-wire state scatter; structured RCS/QAOA not deep arbitrary circuits. No external attestation.','circuits':refs}

def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);args=p.parse_args();out=pathlib.Path(args.evidence).resolve();out.mkdir(parents=True,exist_ok=False);challenge,reference=fixture();c=out/'challenge.json';ref=out/'reference-local.json';com=out/'commitment.json';rev=out/'reveal-local.json';c.write_text(json.dumps(challenge));ref.write_text(json.dumps(reference));
    def call(root,*args,ok=True):
        proc=subprocess.run([sys.executable,'-B',str(root/'tests/blind-campaign.py'),*map(str,args)],capture_output=True,text=True,timeout=900);assert (proc.returncode==0)==ok,(args,proc.stderr[-3000:],proc.stdout[-500:]);return json.loads(proc.stdout) if ok else proc.stderr
    digest=call(ROOT,'freeze')['sourceSHA256'];call(ROOT,'commit',c,ref,com,rev);scores=[];outputs=[]
    with tempfile.TemporaryDirectory(prefix='dsiq-clean-replication-') as d:
        for index in range(2):
            copy=pathlib.Path(d)/str(index);copy.mkdir()
            for sub in ('apps/web/public/dsiq','native','tests','docs'):
                (copy/sub).parent.mkdir(parents=True,exist_ok=True);shutil.copytree(ROOT/sub,copy/sub,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            assert call(copy,'freeze')['sourceSHA256']==digest
            dest=out/f'run-{index}';result=call(copy,'execute',c,com,dest,'--source-sha256',digest,'--timeout','120');assert result['allCompleted'];scores.append(call(copy,'score',c,com,rev,dest,'--output-sha256',result['outputManifestSHA256']));assert scores[-1]['numericalPass'] and not scores[-1]['test100Certified'];outputs.append(result);(out/f'score-{index}.json').write_text(json.dumps(scores[-1],indent=2))
    p=subprocess.run([sys.executable,'-B',str(ROOT/'tests/replication-check.py'),str(out/'run-0'),str(out/'run-1')],capture_output=True,text=True,timeout=120);assert p.returncode==0,p.stderr;compare=json.loads(p.stdout);assert compare['numericalReproducibility'] and not compare['test105Certified'];(out/'replication.json').write_text(p.stdout)
    # Tamper detection: reference alteration, wrong output commitment, changed source,
    # undersized strict challenge, and altered artifact bytes must all be rejected.
    bad=out/'altered-reveal.json';v=json.loads(rev.read_text());v['reference']['circuits'][challenge['circuits'][0]['id']]['q0']['real']+=.01;bad.write_text(json.dumps(v));call(ROOT,'score',c,com,bad,out/'run-0','--output-sha256',outputs[0]['outputManifestSHA256'],ok=False);call(ROOT,'score',c,com,rev,out/'run-0','--output-sha256','0'*64,ok=False);call(ROOT,'execute',c,com,out/'wrong-source','--source-sha256','0'*64,ok=False);short=out/'undersized.json';short.write_text(json.dumps(dict(challenge,circuits=challenge['circuits'][:1])));call(ROOT,'commit',short,ref,out/'bad-commit.json',out/'bad-reveal.json',ok=False);file=out/'run-0'/f"{challenge['circuits'][0]['id']}.json";original=file.read_bytes();file.write_bytes(original+b'\n');
    try:call(ROOT,'score',c,com,rev,out/'run-0','--output-sha256',outputs[0]['outputManifestSHA256'],ok=False)
    finally:file.write_bytes(original)
    queries=[q for case in scores[0]['results'] for q in case['queries']];print(json.dumps({'scope':'LOCAL REHEARSAL; two clean directory copies on the same host, neither independent evaluator nor independent hardware','strictFormatCircuits':len(challenge['circuits']),'queriesPerRun':len(queries),'allQueriesPerRunPassed':all(q['pass'] for q in queries),'maxAbsoluteError':max(q['error'] for q in queries),'maxRelativeAmplitudeError':max(q['relativeError'] for q in queries if q['relativeError'] is not None),'sourceSHA256':digest,'scientificSHA256':compare['first']['scientificSHA256'],'bitExactScientificOutputs':compare['numericalReproducibility'],'tamperAndInvalidInputRejections':5,'test100Certified':False,'test105Certified':False},indent=2))
if __name__=='__main__':main()
