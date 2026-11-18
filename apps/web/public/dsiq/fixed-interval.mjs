// Closed outward-rounded intervals on a 192-bit binary fixed-point grid.
// Integer add/multiply/divide and Taylor/Machin remainder bounds; no libm
// trigonometric values enter the certified numerical coefficients.
import {nextUp,nextDown} from './certified-factor.mjs';
const B=192n,S=1n<<B,SN=2**Number(B),dv=new DataView(new ArrayBuffer(8));
export const iz=[0n,0n],io=[S,S],Z=[iz,iz],O=[io,iz];
export const is0=a=>a[0]===0n&&a[1]===0n,is1=a=>a[0]===S&&a[1]===S;
const CAP=1n<<256n;
const guard=a=>{if(a[0]<-CAP||a[1]>CAP||a[0]>a[1])throw Error('Fixed-point interval dynamic-range boundary');return a};
const floor=(x,y)=>{let q=x/y;return x<0n&&x%y?q-1n:q},ceil=(x,y)=>-floor(-x,y),abs=x=>x<0n?-x:x,max=(a,b)=>a>b?a:b,min=(a,b)=>a<b?a:b;
export const neg=a=>[-a[1],-a[0]],add=(a,b)=>guard([a[0]+b[0],a[1]+b[1]]);
const sub=(a,b)=>add(a,neg(b));
export function mul(a,b){if(is0(a)||is0(b))return iz;if(is1(a))return b;if(is1(b))return a;const v=[a[0]*b[0],a[0]*b[1],a[1]*b[0],a[1]*b[1]];return guard([v.reduce(min)>>B,-((-v.reduce(max))>>B)])}
const div=(a,d)=>[floor(a[0],d),ceil(a[1],d)],integer=k=>[BigInt(k)*S,BigInt(k)*S];
export function exact(x){if(!Number.isFinite(x))throw Error('Nonfinite interval input');if(x===0)return iz;dv.setFloat64(0,x);const a=dv.getBigUint64(0),p=Number((a>>52n)&2047n),mant=(a&((1n<<52n)-1n))|(p?1n<<52n:0n),m=a>>63n?-mant:mant,e=(p?p-1075:-1074)+Number(B);if(e>=0){const y=m<<BigInt(e);return[y,y]}const y=1n<<BigInt(-e);return[floor(m,y),ceil(m,y)]}
export const ca=(a,b)=>[add(a[0],b[0]),add(a[1],b[1])],cm=(a,b)=>[sub(mul(a[0],b[0]),mul(a[1],b[1])),add(mul(a[0],b[1]),mul(a[1],b[0]))],cj=a=>[a[0],neg(a[1])],cn=a=>a.map(neg),zero=a=>is0(a[0])&&is0(a[1]),timesI=a=>[neg(a[1]),a[0]],local=(v,m)=>[ca(cm(m[0],v[0]),cm(m[1],v[1])),ca(cm(m[2],v[0]),cm(m[3],v[1]))];
// Machin identity π=16 atan(1/5)-4 atan(1/239). Alternating series
// truncated after 160 terms, next term controls the absolute tail.
function atanInv(d){let p=d,sum=iz;for(let j=0;j<160;j++){const a=div(io,BigInt(2*j+1)*p);sum=add(sum,j%2?neg(a):a);p*=d*d}const r=ceil(S,321n*p);return [sum[0]-r,sum[1]+r]}
const PI=sub(mul(integer(16),atanInv(5n)),mul(integer(4),atanInv(239n)));
function sqrtInt(x){let a=1n<<BigInt(Math.ceil(x.toString(2).length/2));for(;;){const b=(a+x/a)>>1n;if(b>=a)return a;a=b}}
const h=sqrtInt(S*S/2n),H=[[h,h+1n],iz],I=[iz,io],half=[S/2n,S/2n],m=[half,half],mm=[half,neg(half)];
const cache=new Map();
function trig(t){if(!Number.isFinite(t)||Math.abs(t)>1e6)throw Error('Angle outside interval certificate domain');if(cache.has(t))return cache.get(t);const k=Math.round(t/(2*Math.PI)),x=sub(exact(t),mul(integer(2*k),PI)),xx=mul(x,x),a=max(abs(x[0]),abs(x[1]));if(a>4n*S)throw Error('Angle reduction boundary');let c=io,s=x,tc=io,ts=x;for(let j=1;j<=56;j++){tc=div(neg(mul(tc,xx)),BigInt((2*j-1)*(2*j)));ts=div(neg(mul(ts,xx)),BigInt((2*j)*(2*j+1)));c=add(c,tc);s=add(s,ts)}let tail=S;for(let j=1;j<=113;j++)tail=ceil(tail*a,S*BigInt(j));const enc=(a,r)=>[max(-S,a[0]-r),min(S,a[1]+r)];const out=[enc(c,tail),enc(s,ceil(tail*a,114n*S))];if(cache.size<4096)cache.set(t,out);return out}
const real=a=>[a,iz];
export function fixedMatrix(g){const {name}=g,t=g.theta??0;let c,s;if(['rx','ry','rz','crx','cry','crz','u','cu'].includes(name)){if(!Number.isFinite(t)||t/2*2!==t||Math.abs(t)>1e6)throw Error('Angle outside interval certificate domain');[c,s]=trig(t/2)}switch(name){case'i':return[O,Z,Z,O];case'h':return[H,H,H,cn(H)];case'x':case'cx':return[Z,O,O,Z];case'y':case'cy':return[Z,cn(I),I,Z];case'z':case'cz':return[O,Z,Z,cn(O)];case's':return[O,Z,Z,I];case'sdg':return[O,Z,Z,cn(I)];case't':return[O,Z,Z,[H[0],H[0]]];case'tdg':return[O,Z,Z,[H[0],neg(H[0])]];case'rx':case'crx':return[real(c),[iz,neg(s)],[iz,neg(s)],real(c)];case'ry':case'cry':return[real(c),real(neg(s)),real(s),real(c)];case'rz':case'crz':return[[c,neg(s)],Z,Z,[c,s]];case'p':case'cp':return[O,Z,Z,trig(t)];case'sx':case'csx':return[m,mm,mm,m];case'sy':return[m,cn(m),m,m];case'u':case'cu':return[real(c),cm(real(neg(s)),trig(g.lambda)),cm(real(s),trig(g.phi)),cm(real(c),cm(trig(g.phi),trig(g.lambda)))];default:throw Error('Unsupported fixed interval gate '+name)}}
// BigInt midpoint is projected to binary64; include that projection in the
// outward error radius. L1 radius is a valid complex Euclidean error bound.
export function result(v){const mid=a=>Number((a[0]+a[1])/2n)/SN,re=mid(v[0]),im=mid(v[1]);const rad=(a,x)=>{const p=exact(x);return max(abs(p[0]-a[1]),abs(p[1]-a[0]))};const er=rad(v[0],re)+rad(v[1],im),e=er===0n?0:nextUp(Number(er)/SN);if(![re,im,e].every(Number.isFinite))throw Error('Interval output overflow');const mag=Math.hypot(re,im); // conservative lower magnitude from single largest component, not rounded hypot
 const lowerPart=a=>a[0]>0n?a[0]:a[1]<0n?-a[1]:0n,lo=max(lowerPart(v[0]),lowerPart(v[1])),lower=lo?Math.max(0,nextDown(Number(lo)/SN)):0;
 const relative=lower>0?nextUp(e/lower):null;
 return {real:re,imag:im,absoluteErrorBound:e,certifiedMagnitudeLowerBound:lower,relativeErrorUpperBound:Number.isFinite(relative)?relative:null,log2Magnitude:mag?Math.log2(mag):null,phase:Math.atan2(im,re),componentUnderflow:!mag&&!zero(v),definition:'192-bit outward fixed-point complex interval including binary64 projection; no deliberate truncation'}}
