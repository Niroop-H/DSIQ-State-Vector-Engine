// DSIQ numerical certificate for the FP64 exact-component backend.
// Outward rounding uses adjacent IEEE-754 binary64 values. The reference
// trigonometric intervals use Taylor remainder bounds, not Math.sin/cos.
// The mathematical angles are the exact real values of supplied binary64 inputs.
import {FactorDSIQ} from './factor.mjs';
import {matrix} from './engine.mjs';
const scratch=new DataView(new ArrayBuffer(8));
export function nextUp(x){if(Number.isNaN(x))throw Error('NaN interval');if(x===Infinity)return x;if(x===0)return Number.MIN_VALUE;scratch.setFloat64(0,x);const b=scratch.getBigUint64(0);scratch.setBigUint64(0,x>0?b+1n:b-1n);return scratch.getFloat64(0)}
export const nextDown=x=>-nextUp(-x);
const exact=x=>[x,x], zero=exact(0), one=exact(1), neg=a=>[-a[1],-a[0]], up=(a,b)=>nextUp(a+b), um=(a,b)=>nextUp(a*b);
const plus=(a,b)=>a[0]===0&&a[1]===0?b:b[0]===0&&b[1]===0?a:[nextDown(a[0]+b[0]),nextUp(a[1]+b[1])];
const minus=(a,b)=>plus(a,neg(b));
function times(a,b){if(a[0]===0&&a[1]===0||b[0]===0&&b[1]===0)return zero;const t=[a[0]*b[0],a[0]*b[1],a[1]*b[0],a[1]*b[1]];if(t.some(x=>!Number.isFinite(x)))throw Error('Interval overflow');return [nextDown(Math.min(...t)),nextUp(Math.max(...t))]}
const divide=(a,b)=>{if(!(b>0)||!Number.isFinite(b))throw Error('Invalid interval divisor');return [nextDown(a[0]/b),nextUp(a[1]/b)]};
const cmul=(a,b)=>[minus(times(a[0],b[0]),times(a[1],b[1])),plus(times(a[0],b[1]),times(a[1],b[0]))];
const cadd=(a,b)=>[plus(a[0],b[0]),plus(a[1],b[1])], cneg=a=>a.map(neg), real=x=>[x,zero];
// These two adjacent binary64 endpoints enclose mathematical π and sqrt(1/2).
const pi=[nextDown(Math.PI),nextUp(Math.PI)],root=[nextDown(Math.SQRT1_2),nextUp(Math.SQRT1_2)];
export function trigInterval(value){if(!Number.isFinite(value)||Math.abs(value)>1e6)throw Error('Certificate admits raw binary64 angles |theta| <= 1e6');const k=Math.round(value/(2*Math.PI)),x=minus(exact(value),times(exact(2*k),pi));if(Math.max(Math.abs(x[0]),Math.abs(x[1]))>4)throw Error('Certificate argument reduction failed');const xx=times(x,x);let termS=x,termC=one,s=x,c=one;for(let j=1;j<=24;j++){termS=divide(neg(times(termS,xx)),(2*j)*(2*j+1));termC=divide(neg(times(termC,xx)),(2*j-1)*(2*j));s=plus(s,termS);c=plus(c,termC)}
 // Taylor remainder (Lagrange): all derivatives of sin/cos have magnitude <=1.
 const m=Math.max(Math.abs(x[0]),Math.abs(x[1]));let tail=1;for(let j=1;j<=49;j++)tail=nextUp(um(tail,m)/j);const enclose=(a,r)=>[Math.max(-1,nextDown(a[0]-r)),Math.min(1,nextUp(a[1]+r))];return [enclose(c,tail),enclose(s,nextUp(um(tail,m)/50))]}
const cis=t=>trigInterval(t), Z=real(zero),O=real(one),I=[zero,one],H=real(root);
function certifiedMatrix(g){const {name}=g,t=g.theta??0;let c,s;if(['rx','ry','rz','p','crx','cry','crz','cp','mcry','u','cu'].includes(name)){if(!Number.isFinite(t)||Math.abs(t)>1e6)throw Error('Angle outside certificate regime');if(t/2*2!==t)throw Error('Angle halving not exact in certificate regime');[c,s]=trigInterval(t/2)}const phase=a=>cis(a),h=exact(.5),m=[h,h],mm=[h,neg(h)];switch(name){case'i':return[O,Z,Z,O];case'h':return[H,H,H,cneg(H)];case'x':case'cx':case'ccx':case'mcx':return[Z,O,O,Z];case'y':case'cy':return[Z,cneg(I),I,Z];case'z':case'cz':return[O,Z,Z,cneg(O)];case's':return[O,Z,Z,I];case'sdg':return[O,Z,Z,cneg(I)];case't':return[O,Z,Z,[root,root]];case'tdg':return[O,Z,Z,[root,neg(root)]];case'rx':case'crx':return[real(c),[zero,neg(s)],[zero,neg(s)],real(c)];case'ry':case'cry':case'mcry':return[real(c),real(neg(s)),real(s),real(c)];case'rz':case'crz':return[[c,neg(s)],Z,Z,[c,s]];case'p':case'cp':return[O,Z,Z,phase(t)];case'sx':case'csx':return[m,mm,mm,m];case'sy':return[m,cneg(m),m,m];case'u':case'cu':return[real(c),cmul(real(neg(s)),phase(g.lambda)),cmul(real(s),phase(g.phi)),cmul(real(c),cmul(phase(g.phi),phase(g.lambda)))];default:throw Error('Unsupported certified gate '+name)}}
const absIntervalDistance=(x,a)=>Math.max(nextUp(Math.abs(x-a[0])),nextUp(Math.abs(x-a[1])));
export function matrixError(g){const a=matrix(g),b=certifiedMatrix(g);let e=0;for(let i=0;i<4;i++)for(let j=0;j<2;j++)e=up(e,absIntervalDistance(a[i][j],b[i][j]));return e}
// The norm of a 2x2 complex unitary's real 4x4 embedding is 1, with
// Frobenius norm 2. A componentwise |matrix| bound and at most seven
// roundings per real row give a conservative 64u*(1+epsilon) norm error.
// Absolute subnormal-rounding allowances are added separately.
export class CertifiedFactorDSIQ {
 constructor(n,gates,options={}){this.d=new FactorDSIQ(n,gates,{...options,precision:'fp64'});this.n=n;this.errors=this.d.groups.map(()=>0);this.mode='certified-factor';this.operations=0;this.invalid=false}
 apply(g){if(this.invalid)throw Error('Certified state invalidated');const [i]=this.d.mapped[g.q]??[];if(i===undefined)throw Error('Invalid gate');try{if(g.name==='swap'){this.d.apply(g);this.operations++;return}const e=matrixError(g),a=up(e,um(64*2**-53,up(1,e))),delta=um(64*Number.MIN_VALUE,this.d.groups[i].a.length),old=this.errors[i];const bound=up(up(old,um(a,up(1,old))),delta);if(!Number.isFinite(bound))throw Error('Certificate overflow');this.d.apply(g);this.errors[i]=bound;this.operations++}catch(e){this.invalid=true;throw e}}
 stateError(){if(this.invalid)throw Error('Certified state invalidated');let e=0;for(const a of this.errors)e=up(up(e,a),um(e,a));return e}
 amplitude(bits){if(this.invalid)throw Error('Certified state invalidated');this.d.check(bits);let result=O;for(const {qs,a} of this.d.groups){let x=0;for(let j=0;j<qs.length;j++)if(bits[this.n-1-qs[j]]==='1')x|=1<<j;result=cmul(result,[exact(a[2*x]),exact(a[2*x+1])])}return this.certificate(result,this.stateError())}
 expectation(pauli){if(this.invalid||typeof pauli!=='string'||pauli.length!==this.n||!/^[IXYZ]+$/.test(pauli))throw Error('Invalid certified observable');let out=one;for(const {qs,a} of this.d.groups){let flips=0,z=0,ys=0;for(let j=0;j<qs.length;j++){const p=pauli[this.n-1-qs[j]];if(p==='X'||p==='Y')flips|=1<<j;if(p==='Z'||p==='Y')z|=1<<j;if(p==='Y')ys++}let sum=zero;for(let x=0;x<a.length/2;x++){const y=x^flips;let b=x&z,v=0;while(b){b&=b-1;v^=1}const c=cmul([exact(a[2*y]),exact(-a[2*y+1])],[exact(a[2*x]),exact(a[2*x+1])]),t=[c[0],neg(c[1]),neg(c[0]),c[1]][ys%4];sum=plus(sum,v?neg(t):t)}out=times(out,sum)}const e=this.stateError(),bound=um(e,up(2,e));return this.certificate([out,zero],bound)}
 certificate(interval,e){const re=interval[0][0]/2+interval[0][1]/2,im=interval[1][0]/2+interval[1][1]/2,err=up(e,up(absIntervalDistance(re,interval[0]),absIntervalDistance(im,interval[1])));if(![re,im,err].every(Number.isFinite))throw Error('Unrepresentable certificate');return {real:re,imag:im,absoluteErrorBound:err,stateVectorL2ErrorBound:this.stateError(),roundedCoefficientInterval:interval,definition:'Conservative absolute bound relative to exact unitary evolution at supplied binary64 angles; IEEE-754 basic operation rounding assumed; no claim for input-angle uncertainty'}}
 norm(){return this.expectation('I'.repeat(this.n))}
 stats(){return {...this.d.stats(),mode:this.mode,certifiedGateCount:this.operations,stateVectorL2ErrorBound:this.stateError()}}
}
