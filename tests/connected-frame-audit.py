"""Test-only full physical dense oracle and streamed DSIQ comparator.
Optional Aer reference reuses the same fixture, never linked into production.
"""
from contextlib import contextmanager
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np, ctypes as ct, subprocess,json,sys,tempfile,time,pathlib,math
try:
    import resource
except ImportError:
    resource = None
ROOT=pathlib.Path(__file__).resolve().parents[1]

def local_dense(n,gs):
    a=np.zeros(1<<n,dtype=np.complex128);a[0]=1
    # Explicit full-register dense evolution; no factorization.
    for g in gs:
        q,name,c=g['q'],g['name'],g['controls'];t=g['theta'];h=1<<q
        if name in ('ry','rz','s'):
            v=a.reshape(-1,2,h); x,y=v[:,0,:],v[:,1,:]
            if name=='ry':p=x.copy();co=math.cos(t/2);si=math.sin(t/2);x[:]=co*p-si*y;y[:]=si*p+co*y
            elif name=='rz':x*=complex(math.cos(t/2),-math.sin(t/2));y*=complex(math.cos(t/2),math.sin(t/2))
            else:y*=1j
        elif name in ('cx','cz','swap'):
            # Blockwise source-index selection to limit auxiliary memory.
            b=1<<c[0];
            for k in range(0,len(a),1<<20):
                ix=np.arange(k,min(k+(1<<20),len(a)),dtype=np.int64);
                if name=='cz':sel=ix[((ix&h)!=0)&((ix&b)!=0)];a[sel]*=-1
                elif name=='cx':sel=ix[((ix&h)==0)&((ix&b)!=0)];j=sel|h;v=a[sel].copy();a[sel]=a[j];a[j]=v
                else:sel=ix[((ix&h)==0)&((ix&b)!=0)];j=sel^(h|b);v=a[sel].copy();a[sel]=a[j];a[j]=v
        else:raise ValueError(name)
    return a

def aer_dense(n,gs):
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    c=QuantumCircuit(n)
    for g in gs:
        name,q,cs,t=g['name'],g['q'],g['controls'],g['theta']
        if name in ('ry','rz'):getattr(c,name)(t,q)
        elif name=='s':c.s(q)
        elif name in ('cx','cz','swap'):getattr(c,name)(cs[0],q)
        else:raise ValueError(name)
    c.save_statevector();r=AerSimulator(method='statevector',precision='double',max_parallel_threads=2).run(c).result()
    if not r.success:raise RuntimeError('Aer execution failed')
    return np.asarray(r.data(0)['statevector'],dtype=np.complex128)

@contextmanager
def reference_reader(n, gates, oracle):
    if oracle == 'quest-cut':
        from quest_cut import cut_reader
        reader, _ = cut_reader(n,gates)
        yield reader
        return
    if oracle != 'quest':
        if oracle not in ('aer','local'):raise ValueError('Unknown reference')
        vector = aer_dense(n,gates) if oracle=='aer' else local_dense(n,gates)
        if vector.size != 1 << n:raise ValueError('Incomplete reference vector')
        yield lambda start,count: vector[start:start+count]
        return
    command = os.environ['DSIQ_QUEST_VECTOR']
    lines = [f'{n} {len(gates)}']
    for g in gates:
        control = g['controls'][0] if g['controls'] else -1
        lines.append(f"{g['name']} {g['q']} {control} {g['theta']}")
    with subprocess.Popen([command],stdin=subprocess.PIPE,stdout=subprocess.PIPE) as proc:
        try:
            proc.stdin.write(('\n'.join(lines)+'\n').encode('ascii'))
            proc.stdin.close()
            def read_block(start,count):
                data = proc.stdout.read(count*16)
                if len(data)!=count*16:raise RuntimeError(f'Incomplete QuEST output at {start}')
                return np.frombuffer(data,dtype=np.complex128)
            yield read_block
            if proc.stdout.read(1) or proc.wait()!=0:raise RuntimeError('Invalid QuEST completion')
        finally:
            if proc.poll() is None:proc.kill()

def audit(n=25,oracle='local'):
    if not 1<=n<=30:raise ValueError('Audit width outside 1..30')
    if oracle=='local' and n>25:raise ValueError('Local dense audit limited to 25 qubits')
    t=time.monotonic();x=json.loads(subprocess.check_output(['node',str(ROOT/'tests/connected-frame-fixture.mjs'),str(n)]));d=x['frame'];gs=x['gates'];total=1<<n
    with reference_reader(n,gs,oracle) as read_ref, tempfile.TemporaryDirectory() as td:
        so=os.environ.get('DSIQ_FRAME_STREAM_LIBRARY')
        if not so:
            so=pathlib.Path(td)/'stream.so'
            subprocess.run(['gcc','-O3','-std=c11','-Wall','-Wextra','-Werror','-ffp-contract=off','-shared','-fPIC',str(ROOT/'native/frame_stream.c'),'-lm','-o',str(so)],check=True)
        f=ct.CDLL(str(so)).dsiq_frame_block;ptr=ct.c_void_p;f.argtypes=[ct.c_uint,ct.c_uint64,ct.c_size_t,ct.c_uint64,ct.c_uint,ct.c_double,ct.c_double,ptr,ptr,ptr,ct.c_uint,ptr,ptr,ptr,ct.c_size_t,ptr,ptr];f.restype=ct.c_int
        xs=np.array([int(p['x'],16) for p in d['X']],np.uint64);zs=np.array([int(p['z'],16) for p in d['X']],np.uint64);ps=np.array([p['p'] for p in d['X']],np.uint32);sizes=np.array([len(g['qs']) for g in d['groups']],np.uint32);wires=np.array([q for g in d['groups'] for q in g['qs']],np.uint32);offsets=np.array([sum(len(h['a'])//2 for h in d['groups'][:i]) for i in range(len(sizes))],np.uintp);coeff=np.array([v for g in d['groups'] for v in g['a']],np.float64).view(np.complex128);block=np.empty(min(1<<18,1<<n),np.complex128)
        args=[n,0,0,int(d['offset'],16),d['gamma'],*d['global'],xs.ctypes.data,zs.ctypes.data,ps.ctypes.data,len(sizes),sizes.ctypes.data,wires.ctypes.data,offsets.ctypes.data,coeff.size,coeff.ctypes.data,block.ctypes.data]
        # A second check verifies JS query and native stream conventions.
        for probe in x['probes']:
            ix=int(probe['bits'],2);args[1:3]=[ix,1];assert f(*args)==0;assert abs(block[0]-complex(probe['real'],probe['imag']))<1e-13
        mx=0.;l2=0.;norm=0.;ref_norm=0.;nonzero=0;seen=0;start=time.monotonic()
        for i in range(0,total,block.size):
            k=min(block.size,total-i);args[1:3]=[i,k];assert f(*args)==0;v=block[:k];ref=read_ref(i,k);ref_norm+=float(np.vdot(ref,ref).real);e=np.abs(v-ref);mx=max(mx,float(e.max()));l2+=float(np.dot(e,e));norm+=float(np.vdot(v,v).real);nonzero+=int(np.count_nonzero(ref));seen+=k
        if not (math.isfinite(l2) and mx<=1e-13 and abs(norm-1)<1e-12 and abs(ref_norm-1)<1e-11 and seen==total):raise AssertionError((mx,norm,seen))
        return dict(qubits=n,gates=len(gs),coefficientsCompared=seen,nonzeroReference=nonzero,maxAbsoluteError=mx,l2Error=math.sqrt(l2),norm=norm,referenceNorm=ref_norm,reference=oracle,connected=n>1,coefficientBytes=coeff.nbytes,streamBufferBytes=block.nbytes,logicalVectorBytes=16*total,referenceDenseBytes=None if oracle=='quest-cut' else 16*total,totalSeconds=time.monotonic()-t,streamSeconds=time.monotonic()-start,peakProcessRssKiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None)
if __name__=='__main__':print(json.dumps(audit(int(sys.argv[1]) if len(sys.argv)>1 else 25,sys.argv[2] if len(sys.argv)>2 else 'local'),allow_nan=False))
