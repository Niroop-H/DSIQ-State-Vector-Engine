import {FactorDSIQ} from '../apps/web/public/dsiq/factor.mjs';
import {rng} from '../apps/web/public/dsiq/worker.mjs';
const n=50,gs=[];
for(let k=0;k<10;k++){
  const off=5*k;
  for(let d=0;d<24;d++){
    for(let q=0;q<5;q++)gs.push({name:['rx','ry','rz'][(d+q)%3],q:off+q,controls:[],theta:(d+q+1)*.023});
    for(let q=0;q<4;q++)gs.push({name:'cx',q:off+q+1,controls:[off+q]});
  }
}
const engine=new FactorDSIQ(n,gs),p=performance.now();for(const g of gs)engine.apply(g);const evolveMs=performance.now()-p;
const random=rng(1313),t=performance.now();let s='';for(let i=0;i<5000;i++)s=engine.sample(random);const sampleMs=performance.now()-t;
const v=engine.amplitude(s);console.log(JSON.stringify({n,gates:gs.length,evolveMs,sampleMs,final:s,amplitude:v,stats:engine.stats()}));
