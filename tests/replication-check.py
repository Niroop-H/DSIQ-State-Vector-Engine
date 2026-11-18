#!/usr/bin/env python3
"""Verify reproducibility evidence; no assertion of independent authorship."""
import argparse, hashlib, json, pathlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(x):return hashlib.sha256(x).hexdigest()
def data(p):return json.loads(p.read_bytes())
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def require(ok,msg):
    if not ok:raise ValueError(msg)
def blind(path):
    p=pathlib.Path(path);m=data(p/'output-manifest.json');s=data(p/'source-manifest.json');require(m['schema']=='DSIQ-blind-output-v1' and m['sourceUnchanged'] and m['sourceSHA256']==s['sourceSHA256']==sha(canonical(s['files'])+b'\n'),'Invalid source manifest');results={};hosts=[];complete=True
    require(bool(m['circuits']),'Empty run')
    for k,v in sorted(m['circuits'].items()):
        require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}',k) and v['file']==k+'.json','Invalid evidence filename');f=p/v['file'];require(sha(f.read_bytes())==v['sha256'],'Evidence hash mismatch');a=data(f);w=a.get('workerReport') or {};hosts.append(a.get('host'));complete &= a.get('status')==v['status']==w.get('status')=='COMPLETED' and a.get('workerExitCode')==0
        keys={'real','imag','absoluteErrorBound','stateVectorL2ErrorBound','idealGateStateL2ErrorBound','representedProjectionErrorBound','roundedCoefficientInterval','exact','log2Magnitude','phase','componentUnderflow'}
        results[k]={'status':a.get('status'),'inputSHA256':a.get('inputSHA256'),'outputs':sorted([{'id':q['id'],'kind':q['kind'],'prefix':q['prefix'],'value':{k:v for k,v in q['value'].items() if k in keys}} for q in w.get('outputs',[])],key=lambda q:q['id'])}
        complete &= bool(results[k]['outputs'])
    return {'sourceSHA256':m['sourceSHA256'],'challengeSHA256':m['challengeSHA256'],'commitmentSHA256':m['commitmentSHA256'],'complete':complete,'results':results,'hosts':hosts,'manifestSHA256':sha((p/'output-manifest.json').read_bytes()),'scientificSHA256':sha(canonical(results))}
def campaign(path):
    p=pathlib.Path(path);m=data(p/'campaign-summary.json');s=data(p/'source-manifest.json');r=data(p/'diamond-results.json');orig=data(ROOT/'docs/diamond-105.json');rows=r['results'];require(len(rows)==len(orig)==105 and all(all(a[k]==b[k] for k in ('id','title','requirement')) for a,b in zip(rows,orig)),'Original requirements mismatch');counts={k:sum(a['status']==k for a in rows) for k in ('PASS','PARTIAL','FAIL','BLOCKED','NOT_RUN')};require(sum(counts.values())==105 and counts==r['counts']==m['counts'],'Count mismatch');require(m['sourceUnchanged'] and m['baselineReportSHA256']==sha((p/'diamond-results.json').read_bytes()),'Unfrozen source or report mismatch');jobs=m['jobs']
    for j in jobs:
        if 'stdoutSHA256' in j:
            name=j['name'];require(re.fullmatch(r'[A-Za-z0-9_-]+',name),'Invalid job name');require(sha((p/(name+'.stdout')).read_bytes())==j['stdoutSHA256'] and sha((p/(name+'.stderr')).read_bytes())==j['stderrSHA256'],'Job log hash mismatch')
    return {'sourceSHA256':sha(canonical(s)),'counts':counts,'statuses':[[a['id'],a['status']] for a in rows],'all105Pass':counts['PASS']==105,'allJobsCompleted':all(j.get('completed',False) for j in jobs),'reportSHA256':m['baselineReportSHA256'],'scope':'Status agreement is not equality of every deterministic scientific value.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('first');p.add_argument('second');p.add_argument('--kind',choices=['blind','campaign'],default='blind');a=p.parse_args();require(pathlib.Path(a.first).resolve()!=pathlib.Path(a.second).resolve(),'Two different run directories required');fn=blind if a.kind=='blind' else campaign;x,y=fn(a.first),fn(a.second);same=x['sourceSHA256']==y['sourceSHA256'];out={'schema':'DSIQ-replication-comparison-v1','kind':a.kind,'sourceMatches':same,'first':x,'second':y,'independenceVerified':False,'test105Certified':False}
    if a.kind=='blind':out['numericalReproducibility']=same and x['complete'] and y['complete'] and x['challengeSHA256']==y['challengeSHA256'] and x['commitmentSHA256']==y['commitmentSHA256'] and x['scientificSHA256']==y['scientificSHA256'];passed=out['numericalReproducibility']
    else:out['statusReproducibility']=same and x['statuses']==y['statuses'];passed=out['statusReproducibility']
    print(json.dumps(out,indent=2,allow_nan=False));return 0 if passed else 1
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print(json.dumps({'status':'FAILED','error':str(e)}),file=sys.stderr);sys.exit(2)
