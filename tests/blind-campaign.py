#!/usr/bin/env python3
"""Commit / execute / reveal for Diamond #100. Never asserts reviewer identity.
Reviewer retains references and salt outside the engine/operator environment.
Commit hashes must be exchanged over an authenticated independent channel.
"""
import argparse, hashlib, json, math, pathlib, re, secrets, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
FAMILIES={'QFT','RCS','QAOA','UNCOMPUTE'}
def require(ok,msg):
    if not ok:raise ValueError(msg)
def sha(b):return hashlib.sha256(b).hexdigest()
def encode(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def read(path):return pathlib.Path(path).read_bytes()
def load(path):return json.loads(read(path),parse_constant=lambda v: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
def write(path,data):
    with pathlib.Path(path).open('xb') as f:f.write(encode(data))
def freeze():
    paths=[]
    for d in ('apps/web/public/dsiq','native','tests'):
        paths.extend(p for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'))
    paths.extend(ROOT/'docs'/x for x in ('diamond-105.json','COMPLEXITY.md','INDEPENDENT-REVIEW.md','REVIEWER-ATTESTATION.md'))
    manifest={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(paths)}
    return {'files':manifest,'sourceSHA256':sha(encode(manifest))}
def finite(x):return type(x) in (int,float) and math.isfinite(x)
def validate_suite(challenge,strict=True):
    require(challenge.get('schema')=='DSIQ-blind-challenge-v1','Wrong challenge schema')
    require(isinstance(challenge.get('suiteId'),str) and 0<len(challenge['suiteId'])<=128,'Missing suite ID')
    require(set(challenge)=={'schema','suiteId','circuits'},'Unexpected challenge fields')
    cs=challenge['circuits'];require(isinstance(cs,list) and (len(cs)==20 if strict else 0<len(cs)<=20),'Strict evaluation requires exactly 20 circuits')
    ids=set();families=set()
    for c in cs:
        require(set(c)=={'id','family','request'},'Unexpected circuit fields (reference data must be withheld)');cid=c['id'];require(isinstance(cid,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,80}',cid) and cid not in ids,'Duplicate or invalid circuit ID');ids.add(cid)
        require(c['family'] in FAMILIES,'Invalid circuit family');families.add(c['family']);r=c['request'];require(set(r)<= {'n','gates','queries','method','requireCertificate','checkpointEvery','maxBytes','maxWork','maxNodes'},'Unexpected request field')
        n=r['n'];require(type(n)==int and ((50<=n<=100) if strict else 1<=n<=100),'Wrong circuit width')
        gs=r['gates'];qs=r['queries'];require(isinstance(gs,list) and 0<len(gs)<=100000 and isinstance(qs,list) and 0<len(qs)<=10000,'Missing gates or queries');qid=set();final=False;intermediate=False
        for g in gs:require(isinstance(g,dict) and set(g)<= {'name','q','controls','theta','phi','lambda','piTheta','piPhi','piLambda'},'Invalid gate fields')
        for q in qs:
            require(isinstance(q,dict) and set(q)<= {'id','kind','prefix','bits','pauli'},'Expected answers cannot appear in query fields');i=q['id'];require(isinstance(i,str) and i and i not in qid,'Duplicate or invalid query ID');qid.add(i)
            require(q['kind'] in ('amplitude','pauli','norm') and type(q['prefix'])==int and 0<=q['prefix']<=len(gs),'Invalid query type or prefix')
            final|=q['prefix']==len(gs) and q['kind']!='norm';intermediate|=0<q['prefix']<len(gs) and q['kind']!='norm'
        require(final,'Require a nontrivial final scientific query')
        if strict and c['family']=='UNCOMPUTE':require(intermediate,'Uncompute requires an intermediate scientific query')
    if strict:require(families==FAMILIES,'All four circuit families required')
    return cs

def validate_reference(cs,reference,strict=False):
    require(reference.get('schema')=='DSIQ-blind-reference-v1' and isinstance(reference.get('referenceMethod'),str) and reference['referenceMethod'].strip(),'Missing reference method')
    require(set(reference)=={'schema','suiteId','referenceMethod','circuits'},'Unexpected reference fields');refs=reference['circuits'];require(isinstance(refs,dict) and set(refs)=={c['id'] for c in cs},'Missing/extra reference circuits')
    for c in cs:
        qmap=refs[c['id']];require(isinstance(qmap,dict) and set(qmap)=={q['id'] for q in c['request']['queries']},'Missing/extra reference queries')
        for q in c['request']['queries']:
            v=qmap[q['id']];require(isinstance(v,dict) and {'real','imag','absoluteTolerance'}<=set(v)<= {'real','imag','absoluteTolerance','relativeTolerance'},'Malformed reference');require(all(finite(v[key]) for key in v),'Nonfinite reference');require(0<v['absoluteTolerance']<=1e-13,'Tolerance must be positive and <=1e-13');require(q['kind']=='amplitude' or v['imag']==0,'Observable/norm reference must be real')
            if 'relativeTolerance' in v:require(0<v['relativeTolerance']<=1e-9 and math.hypot(v['real'],v['imag'])>0,'Relative tolerance requires nonzero reference and <=1e-9')
            if strict and q['kind']=='amplitude' and math.hypot(v['real'],v['imag'])>0:require('relativeTolerance' in v,'Nonzero strict amplitude reference requires relative tolerance')
    return refs

def commit(challenge,reference,out,reveal,strict):
    raw=read(challenge);c=load(challenge);cs=validate_suite(c,strict);r=load(reference);validate_reference(cs,r,strict);require(r['suiteId']==c['suiteId'],'Suite ID mismatch');salt=secrets.token_hex(32);secret={'schema':'DSIQ-blind-reveal-v1','salt':salt,'reference':r};public={'schema':'DSIQ-blind-commit-v1','suiteId':c['suiteId'],'challengeSHA256':sha(raw),'referenceCommitmentSHA256':sha(encode(secret)),'strict':strict};write(reveal,secret);write(out,public);return public

def audited_case(request, timeout, limit_mib):
    digest = sha(request)
    command = [sys.executable, '-B', str(ROOT/'native/scientific-audit.py'),
               '--timeout', str(timeout), '--limit-mib', str(limit_mib)]
    try:
        proc = subprocess.run(command, input=request, capture_output=True, timeout=timeout+20)
    except subprocess.TimeoutExpired:
        return {'status':'FAILED', 'inputSHA256':digest, 'error':'Audit wrapper timed out',
                'timeoutSeconds':timeout+20}
    try:
        audit = json.loads(proc.stdout)
        require(isinstance(audit, dict), 'Invalid worker report')
    except (ValueError, UnicodeError):
        return {'status':'FAILED', 'inputSHA256':digest, 'error':'Invalid worker report',
                'stderr':proc.stderr.decode(errors='replace')[-2000:]}
    if audit.get('inputSHA256') != digest or proc.returncode != 0 or audit.get('status') != 'COMPLETED':
        audit['status'] = 'FAILED'
    return audit

def execute(challenge,commitment,out,expected_source,timeout,limit_mib):
    c=load(challenge);raw=read(challenge);p=load(commitment);require(p['schema']=='DSIQ-blind-commit-v1' and p['suiteId']==c['suiteId'] and p['challengeSHA256']==sha(raw) and type(p['strict'])==bool and re.fullmatch('[0-9a-f]{64}',p['referenceCommitmentSHA256']),'Challenge commitment mismatch');cs=validate_suite(c,p['strict']);manifest=freeze();require(manifest['sourceSHA256']==expected_source,'Frozen source hash mismatch');dir=pathlib.Path(out);dir.mkdir(parents=True,exist_ok=False);write(dir/'source-manifest.json',manifest);results={}
    for cse in cs:
        audit=audited_case(encode(cse['request']),timeout,limit_mib)
        name=cse['id']+'.json';write(dir/name,audit);results[cse['id']]={'sha256':sha(read(dir/name)),'status':audit['status'],'file':name};print(cse['id'],audit['status'],file=sys.stderr)
    unchanged=freeze()==manifest;report={'schema':'DSIQ-blind-output-v1','suiteId':c['suiteId'],'challengeSHA256':sha(raw),'commitmentSHA256':sha(read(commitment)),'sourceSHA256':expected_source,'sourceUnchanged':unchanged,'circuits':results,'independentAttestationVerified':False};write(dir/'output-manifest.json',report);return {'outputManifestSHA256':sha(read(dir/'output-manifest.json')),'allCompleted':unchanged and all(x['status']=='COMPLETED' for x in results.values())}

def score(challenge,commitment,reveal,out,recorded_output_hash):
    c=load(challenge);p=load(commitment);secret=load(reveal);r=secret['reference'];dir=pathlib.Path(out);manifest=load(dir/'output-manifest.json');require(p.get('schema')=='DSIQ-blind-commit-v1' and secret.get('schema')=='DSIQ-blind-reveal-v1' and re.fullmatch('[0-9a-f]{64}',secret['salt']),'Invalid reveal/commitment');require(sha(encode(secret))==p['referenceCommitmentSHA256'],'Reference reveal differs from prior commitment');require(sha(read(dir/'output-manifest.json'))==recorded_output_hash,'Output manifest differs from prereveal hash');require(manifest.get('schema')=='DSIQ-blind-output-v1' and p['challengeSHA256']==manifest['challengeSHA256']==sha(read(challenge)) and manifest['commitmentSHA256']==sha(read(commitment)) and p['suiteId']==c['suiteId']==r['suiteId']==manifest['suiteId'] and manifest['sourceUnchanged'],'Challenge, commitment or source mismatch');source=load(dir/'source-manifest.json');require(source['sourceSHA256']==manifest['sourceSHA256']==sha(encode(source['files'])),'Source manifest mismatch');cs=validate_suite(c,p['strict']);refs=validate_reference(cs,r,p['strict']);require(set(manifest['circuits'])=={cse['id'] for cse in cs},'Missing/extra result circuits');rows=[]
    for cse in cs:
        ident=cse['id'];m=manifest['circuits'][ident];name=ident+'.json';require(m['file']==name and m['sha256']==sha(read(dir/name)),'Result hash mismatch');aud=load(dir/name);w=aud.get('workerReport') or {};qmap={v['id']:v for v in w.get('outputs',[])};expected_ids={q['id'] for q in cse['request']['queries']};complete=aud.get('status')==m['status']==w.get('status')=='COMPLETED' and aud.get('workerExitCode')==0 and aud.get('inputSHA256')==w.get('inputSHA256')==sha(encode(cse['request'])) and set(qmap)==expected_ids and len(qmap)==len(w.get('outputs',[]));errors=[]
        for q in cse['request']['queries']:
            v=qmap.get(q['id'],{});x=v.get('value',{});t=refs[ident][q['id']];ok=v.get('kind')==q['kind'] and v.get('prefix')==q['prefix'] and finite(x.get('real')) and finite(x.get('imag') if q['kind']=='amplitude' else x.get('imag',0));delta=math.hypot(x['real']-t['real'],x.get('imag',0)-t['imag']) if ok else None;rel=delta/math.hypot(t['real'],t['imag']) if ok and 'relativeTolerance' in t else None;errors.append({'id':q['id'],'error':delta,'tolerance':t['absoluteTolerance'],'relativeError':rel,'relativeTolerance':t.get('relativeTolerance'),'pass':bool(ok and delta<=t['absoluteTolerance'] and (rel is None or rel<=t['relativeTolerance']))})
        rows.append({'id':ident,'family':cse['family'],'pass':complete and all(x['pass'] for x in errors),'queries':errors})
    return {'schema':'DSIQ-blind-score-v1','suiteId':c['suiteId'],'strict':p['strict'],'sourceSHA256':manifest['sourceSHA256'],'outputManifestSHA256':recorded_output_hash,'numericalPass':all(row['pass'] for row in rows),'independentAttestationVerified':False,'test100Certified':False,'referenceMethod':r['referenceMethod'],'results':rows,'scope':'Reviewer must independently confirm authorship, circuit-family/depth adequacy, prior commitment exchange and external reference correctness. Hashes do not prove independence.'}

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True);s.add_parser('freeze');a=s.add_parser('commit');a.add_argument('challenge');a.add_argument('reference');a.add_argument('commitment');a.add_argument('reveal');a.add_argument('--local-smoke',action='store_true');a=s.add_parser('execute');a.add_argument('challenge');a.add_argument('commitment');a.add_argument('directory');a.add_argument('--source-sha256',required=True);a.add_argument('--timeout',type=int,default=120);a.add_argument('--limit-mib',type=int,default=2048);a=s.add_parser('score');a.add_argument('challenge');a.add_argument('commitment');a.add_argument('reveal');a.add_argument('directory');a.add_argument('--output-sha256',required=True);args=p.parse_args()
    if args.action=='freeze':v=freeze()
    elif args.action=='commit':v=commit(args.challenge,args.reference,args.commitment,args.reveal,not args.local_smoke)
    elif args.action=='execute':v=execute(args.challenge,args.commitment,args.directory,args.source_sha256,args.timeout,args.limit_mib)
    else:v=score(args.challenge,args.commitment,args.reveal,args.directory,args.output_sha256)
    print(json.dumps(v,indent=2,allow_nan=False));return 1 if v.get('numericalPass') is False or v.get('allCompleted') is False else 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print(json.dumps({'status':'FAILED','error':str(e)}),file=sys.stderr);sys.exit(2)
