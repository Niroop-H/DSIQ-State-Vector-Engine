"""Linux-only measured, network-denied DSIQ headless execution.

No remote execution or disk scratch; child receives input and returns output
through pipes. The parent records system counters before/after the child.
Address-space limits bound total possible resident pages, not only tensors.
libseccomp is a system isolation library, not a quantum simulation dependency.
"""
import argparse, ctypes, errno, json, os, pathlib, resource, socket, subprocess, sys
HERE=pathlib.Path(__file__).resolve().parent

def read(path):
    try: return pathlib.Path(path).read_text()
    except OSError: return None

def kv(path):
    raw=read(path)
    if raw is None: return None
    return {k:int(v) for k,v in (line.split()[:2] for line in raw.splitlines()) if v.isdigit()}

def networks():
    return {line.split(':')[0].strip(): [int(x) for x in line.split(':')[1].split()] for line in (read('/proc/net/dev') or '').splitlines() if ':' in line}

def restrict(mib,cpu):
    cap=mib*1024**2
    resource.setrlimit(resource.RLIMIT_AS,(cap,cap));resource.setrlimit(resource.RLIMIT_CPU,(cpu,cpu+1));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    lib=ctypes.CDLL('libseccomp.so.2',use_errno=True)
    lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    class Arg(ctypes.Structure): _fields_=[('arg',ctypes.c_uint),('op',ctypes.c_int),('datum_a',ctypes.c_uint64),('datum_b',ctypes.c_uint64)]
    lib.seccomp_rule_add_array.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(Arg)]
    lib.seccomp_load.argtypes=[ctypes.c_void_p];lib.seccomp_release.argtypes=[ctypes.c_void_p]
    ctx=lib.seccomp_init(0x7fff0000);deny=0x50000|errno.EPERM
    if not ctx: raise RuntimeError('seccomp initialization failed')
    def add(name,cmp=None):
        nr=lib.seccomp_syscall_resolve_name(name.encode())
        if nr<0: return
        if lib.seccomp_rule_add_array(ctx,deny,nr,int(cmp is not None),ctypes.byref(cmp) if cmp is not None else None): raise RuntimeError('seccomp rule failed: '+name)
    try:
        for name in ('socket','socketpair','connect','sendto','sendmsg','sendmmsg','accept','accept4','bind','listen','creat','openat2','io_uring_setup','io_uring_enter','io_uring_register','truncate','ftruncate','unlink','unlinkat','rename','renameat','renameat2','mkdir','mkdirat','rmdir','link','linkat','symlink','symlinkat','mknod','mknodat','memfd_create','mount','umount2'):
            add(name)
        for name,arg in (('open',1),('openat',2)):
            for flag in (os.O_WRONLY,os.O_RDWR,os.O_CREAT,os.O_TRUNC,os.O_APPEND,getattr(os,'O_TMPFILE',0)):
                if flag: add(name,Arg(arg,7,flag,flag)) # SCMP_CMP_MASKED_EQ
        if lib.seccomp_load(ctx): raise RuntimeError('seccomp load failed')
    finally: lib.seccomp_release(ctx)
    for probe in (lambda:socket.socket(socket.AF_INET,socket.SOCK_STREAM),lambda:os.open('/tmp',os.O_WRONLY)):
        try: probe()
        except PermissionError: pass
        else: raise RuntimeError('offline restriction probe unexpectedly succeeded')

def audit(request,limit_mib=2048,timeout=120):
    if not sys.platform.startswith('linux'): raise RuntimeError('Linux audit only')
    if not 1024<=limit_mib<=4096 or not 1<=timeout<=300: raise ValueError('Invalid audit limits')
    data=json.dumps(request,separators=(',',':'),allow_nan=False)
    if len(data)>32*1024**2: raise ValueError('Input exceeds audit limit')
    before={'vmstat':kv('/proc/vmstat'),'cgroup':kv('/sys/fs/cgroup/memory.events'),'network':networks(),'swaps':read('/proc/swaps')}
    p=subprocess.run(['node','--max-old-space-size=512',str(HERE/'offline-execute.mjs')],input=data,text=True,capture_output=True,timeout=timeout,preexec_fn=lambda:restrict(limit_mib,timeout))
    after={'vmstat':kv('/proc/vmstat'),'cgroup':kv('/sys/fs/cgroup/memory.events'),'network':networks(),'swaps':read('/proc/swaps')}
    if p.returncode: raise RuntimeError(f'Offline process failed ({p.returncode}): {p.stderr[-1000:]}')
    out=json.loads(p.stdout);out['osAudit']={'documentedAddressSpaceLimitMiB':limit_mib,'workerExitCode':p.returncode,'guardProbes':'socket and write-open denied before exec; inherited seccomp','swapBefore':before['swaps'],'swapAfter':after['swaps'],'swapCounterDelta':{k:after['vmstat'][k]-before['vmstat'][k] for k in ('pswpin','pswpout')},'oomCounterDelta':{k:after['cgroup'][k]-before['cgroup'][k] for k in ('oom','oom_kill')} if before['cgroup'] and after['cgroup'] else None,'interfaceDeltas':{k:[y-x for x,y in zip(v,after['network'][k])] for k,v in before['network'].items() if k in after['network']},'interfaceScope':'shared network namespace counters; unrelated traffic may be present; syscall restrictions are per child'};return out
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--limit-mib',type=int,default=2048);ap.add_argument('--timeout',type=int,default=120);args=ap.parse_args()
    try: print(json.dumps(audit(json.load(sys.stdin),args.limit_mib,args.timeout),allow_nan=False))
    except Exception as e: print(f'DSIQ audit rejected: {e}',file=sys.stderr);sys.exit(2)
