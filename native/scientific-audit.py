#!/usr/bin/env python3
"""Bounded Linux headless execution; real process telemetry, no synthetic cycles."""
import argparse, ctypes, errno, hashlib, json, os, pathlib, platform, resource, struct, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def cycle_counter():
    # perf_event_open: PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES, inherit.
    # Counts this wrapper and inherited workers; excludes kernel/hypervisor.
    nr={'x86_64':298,'aarch64':241}.get(platform.machine())
    if nr is None or sys.platform!='linux':return None,'Unsupported hardware counter platform'
    attr=bytearray(128);struct.pack_into('=IIQQQQ',attr,0,0,len(attr),0,0,3,0)
    # read_format: total_time_enabled | total_time_running; attr.flags at 40.
    struct.pack_into('=Q',attr,32,3);struct.pack_into('=Q',attr,40,(1<<1)|(1<<5)|(1<<6))
    buf=ctypes.create_string_buffer(bytes(attr));lib=ctypes.CDLL(None,use_errno=True)
    fd=lib.syscall(ctypes.c_long(nr),ctypes.byref(buf),ctypes.c_int(0),ctypes.c_int(-1),ctypes.c_int(-1),ctypes.c_ulong(8)) # PERF_FLAG_FD_CLOEXEC
    if fd<0:
        e=ctypes.get_errno();return None,f'perf_event_open errno {e}: {os.strerror(e)}'
    return fd,None

def recover_journal(raw,stderr,report=None,failure=None):
    # Recover complete, sequential journal records from the parent-held pipe.
    # A killed worker never becomes COMPLETED from recovered evidence.
    journal=[];diagnostic=[]
    for line in stderr.splitlines():
        if line.startswith(b'DSIQ-AUDIT '):
            try:journal.append(json.loads(line[len(b'DSIQ-AUDIT '):]))
            except (ValueError,UnicodeError):pass
        else:diagnostic.append(line)
    if report is None:
        begin=next((x['data'] for x in journal if x.get('kind')=='begin'),None)
        if begin and begin.get('inputSHA256')==sha(raw):
            events=[];outputs=[]
            for x in journal:
                if x.get('kind')=='event' and x['data'].get('sequence')==len(events):events.append(x['data'])
                elif x.get('kind')=='output':outputs.append(x['data'])
            cp=[x for x in events if x.get('kind')=='checkpoint']
            report={'schema':'DSIQ-scientific-run-v1','status':'FAILED','error':failure,'inputSHA256':sha(raw),'runtime':begin.get('runtime'),'requestedGates':begin.get('requestedGates'),'checkpointEvery':begin.get('checkpointEvery'),'completedPrefix':max((x['prefix'] for x in cp),default=None),'events':events,'outputs':outputs,'metrics':{},'recoveredFromJournal':True}
    stderr=b'\n'.join(diagnostic)
    return report, stderr, journal

def run(raw,timeout=120,limit_mib=2048):
    from importlib.machinery import SourceFileLoader
    if sys.platform!='linux':raise RuntimeError('Linux audit interface requires Linux')
    if not 1<=timeout<=3600 or not 1024<=limit_mib<=4096:raise ValueError('Invalid audit limits')
    if len(raw)>32*1024**2:raise ValueError('Input exceeds audit limit')
    from importlib.util import spec_from_loader,module_from_spec
    spec=spec_from_loader('dsiq_audit',SourceFileLoader('dsiq_audit',str(ROOT/'native/audit-runner.py')));mod=module_from_spec(spec);spec.loader.exec_module(mod)
    fd,reason=cycle_counter();start=time.monotonic();before=resource.getrusage(resource.RUSAGE_CHILDREN);code=None;stdout=b'';stderr=b'';failure=None
    try:
        p=subprocess.run(['node','--max-old-space-size=512',str(ROOT/'native/scientific-run.mjs')],input=raw,capture_output=True,timeout=timeout,env={**os.environ,'DSIQ_STREAM_AUDIT':'1'},preexec_fn=lambda:mod.restrict(limit_mib,timeout));code=p.returncode;stdout=p.stdout;stderr=p.stderr
    except subprocess.TimeoutExpired as e:failure='Wall-time limit exceeded';stdout=e.stdout or b'';stderr=e.stderr or b''
    except (OSError,subprocess.SubprocessError) as e:failure=str(e)
    finally:
        elapsed=time.monotonic()-start;after=resource.getrusage(resource.RUSAGE_CHILDREN);cycles=None;enabled=None;running=None
        if fd is not None:
            try:
                data=os.read(fd,24)
                if len(data)!=24:raise OSError('Short perf counter read')
                cycles,enabled,running=struct.unpack('=QQQ',data)
                if not running:cycles=None;reason='Counter did not run'
            except OSError as e:reason=str(e)
            finally:os.close(fd)
    try:report=json.loads(stdout)
    except (ValueError,UnicodeError):report=None;failure=failure or 'Worker did not return a complete JSON report'
    journal_sha=sha(stderr)
    report,stderr,journal=recover_journal(raw,stderr,report,failure)
    valid=bool(report and report.get('inputSHA256')==sha(raw) and report.get('status')=='COMPLETED' and code==0 and not failure)
    if not valid:failure=failure or (report or {}).get('error') or f'Worker exit {code}'
    return {'schema':'DSIQ-scientific-audit-v1','status':'COMPLETED' if valid else 'FAILED','error':failure,'inputSHA256':sha(raw),'workerExitCode':code,'workerReport':report,'workerStdoutSHA256':sha(stdout),'stderr':stderr.decode(errors='replace')[-4000:],'elapsedSeconds':elapsed,'limitMiB':limit_mib,'wallTimeoutSeconds':timeout,'cpuSoftLimitSeconds':timeout,'cpuHardLimitSeconds':timeout+1,'terminationSignal':-code if code is not None and code<0 else None,'journalRecords':len(journal),'journalPipeSHA256':journal_sha,'childCPUSeconds':{'user':after.ru_utime-before.ru_utime,'system':after.ru_stime-before.ru_stime},'childPeakRssKiB':after.ru_maxrss,'peakRssScope':'RUSAGE_CHILDREN cumulative maximum for this wrapper process; per-worker peak in workerReport.metrics','cpuCycles':{'value':cycles,'timeEnabledNs':enabled,'timeRunningNs':running,'unavailableReason':reason,'scope':'Linux hardware CPU cycles for wrapper and inherited children; user mode; raw not scaled'},'gpu':{'used':False,'cycles':None,'reason':'CPU-only path'},'host':{'system':platform.system(),'machine':platform.machine(),'release':platform.release(),'python':platform.python_version()},'isolation':'Linux RLIMIT_AS and CPU; inherited seccomp socket and write-open denial; trusted-code harness'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--timeout',type=int,default=120);p.add_argument('--limit-mib',type=int,default=2048);a=p.parse_args()
    try:r=run(sys.stdin.buffer.read(),a.timeout,a.limit_mib);print(json.dumps(r,allow_nan=False));sys.exit(0 if r['status']=='COMPLETED' else 1)
    except Exception as e:print(json.dumps({'schema':'DSIQ-scientific-audit-v1','status':'FAILED','error':str(e)}));sys.exit(2)
