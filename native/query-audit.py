#!/usr/bin/env python3
"""Opt-in CPU query-directed audit; separate from measured-checkpoint protocol.
Runs an isolated worker with wall/CPU/address-space limits and captures partial
answers. Analytic norm evidence is explicitly not a measured state checkpoint.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,platform,resource,signal,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parent

def load_module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def run(raw,timeout=120,limit_mib=2048,measure_norms=False):
    if sys.platform!='linux' or type(timeout)!=int or not 1<=timeout<=3600 or not 1024<=limit_mib<=4096:raise ValueError('Invalid worker limits/platform')
    if len(raw)>32*2**20:raise ValueError('Input exceeds size limit')
    request=json.loads(raw);strict=request.get('requireCertificate',True)
    # No fallback from the strict enclosure path to uncertified values.
    file='certified_query_contraction.py' if strict else 'query_contraction.py';guard=load_module('guard','audit-runner.py');audit=load_module('audit','scientific-audit.py')
    command=[sys.executable,'-B',str(ROOT/file)]+(['--measure-norms'] if measure_norms else [])
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}
    start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);fd,reason=audit.cycle_counter();failure=None;code=None;stdout=b'';stderr=b''
    try:
        p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=lambda:guard.restrict(limit_mib,timeout),env=env)
        try:stdout,stderr=p.communicate(raw,timeout=timeout)
        except subprocess.TimeoutExpired:
            failure='WALL_TIMEOUT';os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate()
        code=p.returncode
    except (OSError,subprocess.SubprocessError) as e:failure='WORKER_START_ERROR: '+str(e)
    finally:
        cycles=enabled=running=None
        if fd is not None:
            import struct
            try:
                data=os.read(fd,24);cycles,enabled,running=struct.unpack('=QQQ',data)
                if not running:cycles=None;reason='Counter did not run'
            except (OSError,struct.error) as e:reason=str(e)
            finally:os.close(fd)
    elapsed=time.monotonic()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN);records=[];malformed=0
    for line in stdout.splitlines():
        try:records.append(json.loads(line))
        except (ValueError,UnicodeError):malformed+=1
    queries=request.get('queries',[]);wanted={q['id']:(q['kind'],q['prefix']) for q in queries};seen=set();good=[];invalid=[]
    for record in records:
        i=record.get('id');v=record.get('value');is_valid=i in wanted and i not in seen and wanted[i]==(record.get('kind'),record.get('prefix')) and (not strict or v is None or isinstance(v.get('absoluteErrorBound'),(int,float)) and v['absoluteErrorBound']>=0)
        if not is_valid:invalid.append(i);continue
        seen.add(i)
        if v is not None:good.append(record)
    complete=code==0 and not failure and not malformed and not invalid and len(good)==len(queries)
    if not complete and failure is None:failure='SIGNAL_'+str(-code) if code is not None and code<0 else 'QUERY_OR_RESOURCE_BOUNDARY'
    return {'schema':'DSIQ-query-directed-audit-v1','status':'QUERIES_COMPLETED' if complete else 'INCOMPLETE','scope':'Query-directed native experimental route; not the measured-checkpoint acceptance protocol','inputSHA256':hashlib.sha256(raw).hexdigest(),'strictRequested':strict,'workerExitCode':code,'failureCategory':failure,'records':records,'queriesReturned':len(good),'queriesRequested':len(queries),'missingIds':sorted(set(wanted)-{q['id'] for q in good}),'invalidRecords':invalid,'malformedRecords':malformed,'checkpointEvidence':'NOT_RUN; no per-stride measured checkpoints claimed','normMode':'measured double layer with exact rewrites' if measure_norms else 'analytical unitary norm, not measured','elapsedSeconds':elapsed,'wallTimeoutSeconds':timeout,'cpuSoftLimitSeconds':timeout,'addressSpaceLimitMiB':limit_mib,'childPeakRssKiB':after.ru_maxrss,'childCPUSeconds':{'user':after.ru_utime-before.ru_utime,'system':after.ru_stime-before.ru_stime},'cpuCycles':{'value':cycles,'timeEnabledNs':enabled,'timeRunningNs':running,'unavailableReason':reason},'gpu':{'used':False,'cycles':None},'stderr':stderr.decode(errors='replace')[-4000:],'host':{'system':platform.system(),'machine':platform.machine(),'release':platform.release(),'python':platform.python_version()},'isolation':'Inherited RLIMIT_AS/CPU and seccomp network/write restrictions, process-group termination on timeout'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--timeout',type=int,default=120);p.add_argument('--limit-mib',type=int,default=2048);p.add_argument('--measure-norms',action='store_true');a=p.parse_args()
    try:r=run(sys.stdin.buffer.read(),a.timeout,a.limit_mib,a.measure_norms);print(json.dumps(r,allow_nan=False));sys.exit(0 if r['status']=='QUERIES_COMPLETED' else 1)
    except Exception as e:print(json.dumps({'status':'INVALID','error':str(e)}));sys.exit(2)
