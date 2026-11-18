// DSIQ certificate of a full connected circuit query. Exact dyadic contraction
// of compiled binary64 matrices, plus outward-rounded ideal gate L2 error.
// No certification from a heuristic numerical convergence test.
import {matrixError,nextUp} from './certified-factor.mjs';
import {exactDyadicAmplitude,exactDyadicExpectation,ContractionBudget} from './contraction.mjs';
const up=(a,b)=>nextUp(a+b), um=(a,b)=>nextUp(a*b), dv=new DataView(new ArrayBuffer(8));
const abs=x=>x<0n?-x:x;
function parts(x){if(!Number.isFinite(x))throw new ContractionBudget('Nonfinite projected value');if(x===0)return [0n,0];dv.setFloat64(0,x);const v=dv.getBigUint64(0),p=Number(v>>52n&2047n),m=(v&((1n<<52n)-1n))|(p?1n<<52n:0n);return [v>>63n?-m:m,p?p-1075:-1074]}
function roundingBound(x,m,e){const [a,b]=parts(x),n=BigInt(m);if(!n&&!a)return 0;const k=Math.min(a?b:e,n?e:b),d=abs((a<<BigInt(a?b-k:0))-(n<<BigInt(n?e-k:0)));if(!d)return 0;const power=d.toString(2).length+k;if(power>1023)throw new ContractionBudget('Projection error bound overflow');return power< -1074?Number.MIN_VALUE:2**power}
export function representedGateError(gates){let e=0;for(const g of gates){if(g.name==='swap')continue;const delta=matrixError(g);e=up(up(e,delta),um(e,delta));if(!Number.isFinite(e))throw new ContractionBudget('Ideal gate coefficient error overflow')}return e}
export class CertifiedContraction {
 constructor(n,gates,options={}){this.n=n;this.gates=gates;this.options={maxBytes:67108864,maxWork:50000000,maxVariables:100000,...options};this.error=representedGateError(gates);this.mode='certified-contraction';this.queries=0;this.work=0;this.peak=0}
 certificate(r,e){const a=r.exact;const projection=up(roundingBound(r.real,a.realMantissa,a.binaryExponent),roundingBound(r.imag,a.imagMantissa,a.binaryExponent));this.queries++;this.work+=r.work;this.peak=Math.max(this.peak,r.peakDyadicPayloadBytes??0);const absoluteErrorBound=up(e,projection);if(!Number.isFinite(absoluteErrorBound))throw new ContractionBudget('Unrepresentable numerical bound');return {...r,mode:this.mode,absoluteErrorBound,representedProjectionErrorBound:projection,idealGateStateL2ErrorBound:this.error,definition:'Absolute error enclosure relative to ideal matrices at supplied binary64 angles; exact represented-matrix contraction; outward-rounded gate norm bound'}}
 amplitude(bits){return this.certificate(exactDyadicAmplitude(this.n,this.gates,bits,this.options),this.error)}
 expectation(p){return this.certificate(exactDyadicExpectation(this.n,this.gates,p,this.options),um(this.error,up(2,this.error)))}
 norm(){return this.expectation('I'.repeat(this.n))}
 stats(){return {mode:this.mode,qubits:this.n,gates:this.gates.length,completedContractions:this.queries,work:this.work,peakDyadicPayloadBytes:this.peak,idealGateStateL2ErrorBound:this.error,precision:'Exact dyadic represented matrices plus conservative ideal-gate error enclosure; no intentional truncation'}}
}
