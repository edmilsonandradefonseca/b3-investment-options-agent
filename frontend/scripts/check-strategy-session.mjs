// LAB-01/02/06, WS-05: browser contract test with explicit fixtures, not live acceptance.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const browser=await chromium.launch({headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 await page.addInitScript(()=>localStorage.setItem('b3.apiBaseUrl','http://127.0.0.1:8000'));
 const requests=[], errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('http://127.0.0.1:8000/**',async route=>{
  const req=route.request();
  if(req.method()==='OPTIONS')return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type'}});
  const body=req.postDataJSON();
  if(req.url().endsWith('/orchestrate')&&body?.context?.workspace==='Strategy Lab'){
   requests.push(body);
   return route.fulfill({json:{status:'COMPLETED',result:{summary:'Resposta de fixture: tese exige verificar premissas.',derived_synthesis_status:'COMPLETED'},sources:[],audit:[],error:null},headers:{'Access-Control-Allow-Origin':'*'}});
  }
  const json=req.url().endsWith('/health')?{status:'ok'}:req.url().includes('/transactions')?[]:req.url().endsWith('/orchestrate')?{status:'COMPLETED',result:{},sources:[],audit:[],error:null}:{positions:[],operations:[]};
  return route.fulfill({json,headers:{'Access-Control-Allow-Origin':'*'}});
 });
 await page.goto((process.env.B3_UI_URL||'http://127.0.0.1:5173')+'/#/strategy-lab');
 const panel=page.getByRole('region',{name:'Pergunta e análise do Strategy Lab'});
 await panel.getByLabel('Sua pergunta ou tese').fill('Avalie minha tese sobre PETR4.');
 await panel.getByRole('button',{name:'Analisar pergunta ou tese',exact:true}).click();
 await panel.getByText('Resposta de fixture: tese exige verificar premissas.',{exact:true}).waitFor();
 assert.equal(requests.length,1);assert.equal(requests[0].ticker,null);
 assert.equal(requests[0].context.comparison_assets,undefined);
 assert.equal(requests[0].context.analysis_mode,undefined);
 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('E se cair 5%?');
 await panel.getByRole('button',{name:'Enviar continuação',exact:true}).click();
 await panel.getByRole('article',{name:'Análise 2'}).getByText('Resposta de fixture: tese exige verificar premissas.',{exact:true}).waitFor();
 assert.equal(requests[1].context.lab_conversation[0].question,'Avalie minha tese sobre PETR4.');
 const out=resolve(process.env.B3_VISUAL_OUTPUT||'visual-output');await mkdir(out,{recursive:true});
 for(const [width,height] of [[1440,900],[1180,720]]){await page.setViewportSize({width,height});await page.screenshot({path:resolve(out,`lab-central-fixture-${width}.png`),animations:'disabled'});}

 await panel.getByRole('button',{name:'Nova análise',exact:true}).click();
 assert.equal(await panel.locator('article').count(),0);
 await panel.getByLabel('Sua pergunta ou tese').fill('Nova tese sobre VALE3.');
 await panel.getByRole('button',{name:'Analisar pergunta ou tese',exact:true}).click();
 await panel.getByText('Resposta de fixture: tese exige verificar premissas.',{exact:true}).waitFor();
 assert.equal(requests[2].context.lab_conversation.length,0);
 assert.deepEqual(errors,[]);
 console.log('PASS LAB-01/02/06: central response, no hidden defaults, continuation and reset (fixtures).');
}finally{await browser.close();}
