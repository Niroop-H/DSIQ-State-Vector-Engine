#!/usr/bin/env python3
"""Execute unchanged challenge requests with the experimental native audit.
Scoring is separate. No reviewer reference values or fixture IDs enter workers.
"""
import argparse,concurrent.futures,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def execute(challenge,dest,workers=2,timeout=120,measure=False):
    c=json.loads(pathlib.Path(challenge).read_bytes());dest=pathlib.Path(dest);dest.mkdir(exist_ok=False);start=time.monotonic()
    def run(case):
        raw=(json.dumps(case['request'],sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();cid=case['id'];args=[sys.executable,'-B',str(ROOT/'native/query-audit.py'),'--timeout',str(timeout)]+(['--measure-norms'] if measure else [])
        try:
            proc=subprocess.run(args,input=raw,capture_output=True,timeout=timeout+15);r=json.loads(proc.stdout)
        except (ValueError,subprocess.TimeoutExpired) as e:r={'status':'INVALID','error':str(e),'inputSHA256':sha(raw)}
        data=(json.dumps(r,sort_keys=True,allow_nan=False)+'\n').encode();(dest/(cid+'.json')).write_bytes(data)
        print(cid,r.get('status'),r.get('queriesReturned'),r.get('queriesRequested'),r.get('elapsedSeconds'),r.get('failureCategory'),flush=True);return cid,sha(data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:hashes=dict(pool.map(run,c['circuits']))
    m={'schema':'DSIQ-query-regression-manifest-v1','challengeSHA256':sha(pathlib.Path(challenge).read_bytes()),'files':hashes,'workers':workers,'wallAndCPUSeconds':timeout,'addressSpaceMiB':2048,'elapsedSeconds':time.monotonic()-start,'measureNorms':measure,'scope':'Known challenge regression; not blind or measured-checkpoint acceptance'};(dest/'manifest.json').write_text(json.dumps(m,sort_keys=True,indent=2));print(json.dumps(m),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('challenge');p.add_argument('directory');p.add_argument('--workers',type=int,default=2);p.add_argument('--timeout',type=int,default=120);p.add_argument('--measure-norms',action='store_true');a=p.parse_args();execute(a.challenge,a.directory,a.workers,a.timeout,a.measure_norms)
