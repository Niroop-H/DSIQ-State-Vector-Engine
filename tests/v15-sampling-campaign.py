#!/usr/bin/env python3
"""Known-challenge sampling regression, not the original blind submission.
Worker receives only request + predetermined seed + shot count.
"""
import argparse, pathlib, json, hashlib, subprocess, sys, os, time, importlib.util, resource
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('challenge');p.add_argument('out');args=p.parse_args();raw=pathlib.Path(args.challenge).read_bytes();c=json.loads(raw);d=pathlib.Path(args.out);d.mkdir(exist_ok=False)
 cases=[x for x in c['circuits'] if x['family']=='RCS'];seeds={x['id']:sha(('DSIQ-known-regression-sampling-v1:'+sha(raw)+':'+x['id']).encode()) for x in cases};(d/'predeclared-seeds.json').write_text(json.dumps(seeds,indent=2)+'\n')
 spec=importlib.util.spec_from_file_location('guard',ROOT/'native/audit-runner.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
 records={}
 for x in cases:
  cid=x['id'];payload=json.dumps({'request':x['request'],'seed':seeds[cid],'shots':20000},separators=(',',':'),allow_nan=False).encode();start=time.monotonic()
  try:
   proc=subprocess.run(['node','--max-old-space-size=512',str(ROOT/'native/sparse-samples.mjs')],input=payload,capture_output=True,timeout=120,preexec_fn=lambda:guard.restrict(2048,120));result=json.loads(proc.stdout);result['workerExitCode']=proc.returncode
   if result.get('status')=='COMPLETED':assert result['inputSHA256']==sha(payload) and proc.returncode==0
  except (subprocess.TimeoutExpired,ValueError,KeyError,AssertionError) as e:result={'status':'FAILED','error':str(e)}
  result['wallSeconds']=time.monotonic()-start;result['addressSpaceMiB']=2048;result['wallAndCpuLimitSeconds']=120;result['sourceChallengeSHA256']=sha(raw);result['scope']='Known challenge sampling regression; not blind';b=(json.dumps(result,sort_keys=True,allow_nan=False)+'\n').encode();(d/(cid+'.json')).write_bytes(b);records[cid]={'sha256':sha(b),'status':result['status'],'shots':result.get('shotsCompleted',0)};print(cid,records[cid],flush=True)
 (d/'manifest.json').write_text(json.dumps({'challengeSHA256':sha(raw),'records':records},indent=2)+'\n');return int(any(x['status']!='COMPLETED' for x in records.values()))
if __name__=='__main__':sys.exit(main())
