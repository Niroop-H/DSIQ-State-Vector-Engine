import {readFileSync,writeFileSync,cpSync,mkdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=resolve(process.argv[2]||'.'),here=resolve(dirname(fileURLToPath(import.meta.url)),'..');
const p=resolve(root,'apps/web/src/LargeQuantum.tsx');let s=readFileSync(p,'utf8');
if(!s.includes('dsiqFrame')){
 function replace(a,b){if(!s.includes(a))throw Error('Unexpected source layout: '+a.slice(0,70));s=s.replace(a,b)}
 replace('type Tab="workbench"','type Tab="dsiq"|"workbench"');
 replace('const workerRef=useRef<Worker|null>(null)','const dsiqFrame=useRef<HTMLIFrameElement|null>(null),dsiqPending=useRef(false);\n const workerRef=useRef<Worker|null>(null)');
 replace(' const analysis=useMemo',` useEffect(()=>{
  const receive=async(e:MessageEvent)=>{
   const frame=dsiqFrame.current;
   if(e.origin!==location.origin||e.source!==frame?.contentWindow||e.data?.type!=="dsiq:reserve"||dsiqPending.current)return;
   dsiqPending.current=true;
   try{const allowance=await executionBudget.reserve();frame?.contentWindow?.postMessage({type:allowance.ok?"dsiq:allowed":"dsiq:denied",message:allowance.message},location.origin);}
   finally{dsiqPending.current=false;}
  };
  window.addEventListener("message",receive);return()=>window.removeEventListener("message",receive);
 },[executionBudget.reserve]);
 const analysis=useMemo`);
 replace('workbench:"Quantum computation workbench",','dsiq:"DSIQ State Vector Engine",workbench:"Quantum computation workbench",');
 replace('{key:"workbench",name:"Circuit Workbench",detail:"QASM, solver & output"},','{key:"dsiq",name:"DSIQ State Vector Engine",detail:"Virtual amplitudes & coherent replay"},\n  {key:"workbench",name:"Circuit Workbench",detail:"QASM, solver & output"},');
 replace('01–09','01–10');
 replace('{tab==="workbench"&&<div className="large-grid">','{tab==="dsiq"&&<iframe ref={dsiqFrame} src="/dsiq/index.html" title="DSIQ State Vector Engine" style={{width:"100%",height:"1050px",border:"1px solid #365168",borderRadius:10}}/>}\n     {tab==="workbench"&&<div className="large-grid">');
 writeFileSync(p,s);
}
const src=resolve(here,'apps/web/public/dsiq'),dest=resolve(root,'apps/web/public/dsiq');if(src!==dest){mkdirSync(dest,{recursive:true});cpSync(src,dest,{recursive:true})}console.log('DSIQ integrated into '+root);
const config=resolve(root,'vercel.json');const v=JSON.parse(readFileSync(config,'utf8'));
if(!v.headers.some(h=>h.source==='/dsiq/index.html')){
 const common=v.headers.find(h=>h.source==='/(.*)');if(!common)throw Error('Unexpected Vercel security header layout');
 common.source='/:path((?!dsiq/index\\.html$).*)';const specific=JSON.parse(JSON.stringify(common));specific.source='/dsiq/index.html';
 for(const h of specific.headers){if(h.key==='X-Frame-Options')h.value='SAMEORIGIN';if(h.key==='Content-Security-Policy')h.value=h.value.replace("frame-ancestors 'none'","frame-ancestors 'self'")}
 v.headers.push(specific);writeFileSync(config,JSON.stringify(v,null,2)+'\n');
}
