// Exact rational multiples of pi: reduce before converting to binary64.
// Unsupported symbolic forms return null; ordinary numeric input remains numeric.
const abs=x=>x<0n?-x:x;
function rat(a,b=1n){if(!b)throw Error('division by zero');if(b<0n){a=-a;b=-b}let x=abs(a),y=b;while(y){[x,y]=[y,x%y]}if(x){a/=x;b/=x}if(abs(a).toString(2).length>1024||b.toString(2).length>1024)throw Error('symbolic coefficient exceeds budget');return[a,b]}
const add=(a,b)=>rat(a[0]*b[1]+b[0]*a[1],a[1]*b[1]),neg=a=>[-a[0],a[1]],mul=(a,b)=>rat(a[0]*b[0],a[1]*b[1]),div=(a,b)=>rat(a[0]*b[1],a[1]*b[0]);const zero=[0n,1n],one=[1n,1n];
function decimal(t){const m=/^(\d*\.?\d+|\d+\.)(?:e([+-]?\d+))?$/i.exec(t);if(!m)throw Error('not numeric');const [a,b='']=m[1].split('.'),e=Number(m[2]||0)-b.length;if(!Number.isSafeInteger(e)||Math.abs(e)>300||a.length+b.length>300)throw Error('decimal budget');const v=BigInt((a+b)||'0');return e<0?rat(v,10n**BigInt(-e)):rat(v*10n**BigInt(e))}
export function exactPiAngle(source,period){if(![2,4].includes(period)||typeof source!=='string'||source.length>1024)return null;const ts=source.replace(/\s/g,'').match(/(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|pi|[()+*/-]/gi)||[];if(ts.join('')!==source.replace(/\s/g,''))return null;let i=0;
  function atom(){const t=ts[i++];if(t==='+')return atom();if(t==='-')return atom().map(neg);if(t==='('){const r=expr();if(ts[i++]!==')')throw Error('parentheses');return r}if(t==='pi')return[zero,one];return[decimal(t),zero]}
  function term(){let x=atom();while(ts[i]==='*'||ts[i]==='/'){const op=ts[i++],y=atom();if(op==='*'){if(x[1][0]&&y[1][0])throw Error('nonlinear pi');x=[mul(x[0],y[0]),add(mul(x[0],y[1]),mul(x[1],y[0]))]}else{if(y[1][0])throw Error('symbolic denominator');x=x.map(v=>div(v,y[0]))}}return x}
  function expr(){let x=term();while(ts[i]==='+'||ts[i]==='-'){const op=ts[i++],y=term();x=x.map((v,j)=>add(v,op==='+'?y[j]:neg(y[j])))}return x}
  try{const [a,b]=expr();if(i!==ts.length||a[0]!==0n||!ts.includes('pi'))return null;let [num,den]=b;num%=BigInt(period)*den;if(!num)return 0;const x=Number(num)/Number(den);return Number.isFinite(x)&&x!==0?Math.PI*x:null}catch{return null}
}
