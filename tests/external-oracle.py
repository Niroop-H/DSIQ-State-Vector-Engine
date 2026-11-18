"""Named simulator comparisons; external packages are test-only dependencies.
No fallback to a self-written oracle if a requested module is unavailable.
"""
import json,math,subprocess,sys,pathlib,importlib.metadata,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
def version(s):return importlib.metadata.version(s)
def fixture(mode):return json.loads(subprocess.check_output(['node',str(ROOT/'tests/external-oracle-fixture.mjs'),mode],timeout=180))
def stim_audit():
 import stim
 x=fixture('stim');c=stim.Circuit()
 for g in x['gates']:
  name={'sdg':'S_DAG'}.get(g['name'],g['name'].upper());c.append(name,[*g['controls'],g['q']])
 s=stim.TableauSimulator();s.set_num_qubits(x['n']);s.do_circuit(c);errors=[]
 for p in x['paulis']:
  # Stim uses q0 first; DSIQ textual Pauli strings use q0 last.
  actual=s.peek_observable_expectation(stim.PauliString(p['s'][::-1]));errors.append(abs(actual-p['value']))
 if max(errors)!=0 or x['stabilizerWitnesses']!=100:raise AssertionError('Stim discrepancy')
 return dict(test=57,reference='Stim',version=version('stim'),qubits=x['n'],gates=len(x['gates']),observableComparisons=len(errors),maxError=max(errors),globalPhase='Not determined by stabilizer tableau; internal affine global-phase comparisons separate')
def quimb_audit():
 import quimb.tensor as qtn
 x=fixture('quimb');c=qtn.Circuit(x['n'],gate_contract=False)
 for g in x['gates']:
  name=g['name'].upper();args=([g['theta']] if 'theta' in g else [])+g['controls']+[g['q']];c.apply_gate(name,*args)
 errors=[];rel=[];logs=[]
 for q in x['queries']:
  a=complex(c.amplitude(q['bits'][::-1],optimize='greedy',simplify_sequence='R',simplify_atol=0.0,dtype='complex128'));d=complex(q['real'],q['imag']);e=abs(a-d);errors.append(e)
  if a==0 or d==0:
   if a!=d:raise AssertionError('Zero/nonzero mismatch')
  else:rel.append(e/abs(a));logs.append(abs(math.log2(abs(a))-q['log2Magnitude']))
 if max(errors)>1e-13 or max(rel,default=0)>1e-9 or max(logs,default=0)>1e-9:raise AssertionError('quimb discrepancy')
 return dict(test=56,reference='quimb',version=version('quimb'),qubits=x['n'],gates=len(x['gates']),amplitudeComparisons=len(errors),maxAbsoluteError=max(errors),maxRelativeError=max(rel,default=0),maxLogError=max(logs,default=0),scope='Exact low-depth 10x10 grid amplitude comparison; all controlled gates kept, no SVD cutoff')
if __name__=='__main__':
 mode=sys.argv[1] if len(sys.argv)>1 else ''
 if mode=='stim':r=stim_audit()
 elif mode=='quimb':r=quimb_audit()
 else:raise ValueError('Select stim or quimb')
 print(json.dumps(r,allow_nan=False))
