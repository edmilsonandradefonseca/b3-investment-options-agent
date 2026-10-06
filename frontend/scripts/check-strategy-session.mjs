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
   if(body.task==='Vale manter, encerrar ou rolar uma opção da minha carteira?')return route.fulfill({json:{status:'NEEDS_CLARIFICATION',result:{lab_clarification:{status:'NEEDS_CLARIFICATION',question:'Qual é o código exato da opção que deseja analisar?',reason:'Informe o contrato.'},derived_synthesis_status:'NOT_REQUESTED'},sources:[],audit:[],error:null},headers:{'Access-Control-Allow-Origin':'*'}});
   if(body.task==='A opção é PETRK376.'||body.task==='100 unidades.'){
    const selected=body.task==='100 unidades.';
    const result={lab_position_selection:{option_id:'PETRK376',side:'SHORT',snapshot_as_of:'2026-10-06',available_quantity_units:2500,...(selected?{selected_quantity_units:100}:{}),position:{underlying_ticker:'PETR4',option_type:'CALL',strike:37.6,expiration_date:'2026-11-20',source_ref:'fixture:current-snapshot'}},...(selected?{summary:'Posição e quantidade identificadas; cálculos pendentes.'}:{lab_clarification:{status:'NEEDS_CLARIFICATION',question:'Deseja analisar toda a posição ou quantas unidades?',reason:'Quantidade explícita necessária.'}}),derived_synthesis_status:'NOT_REQUESTED'};
    return route.fulfill({json:{status:selected?'INPUTS_IDENTIFIED':'NEEDS_CLARIFICATION',result,sources:[],audit:[],error:null},headers:{'Access-Control-Allow-Origin':'*'}});
   }
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
 await panel.getByRole('button',{name:'Nova análise',exact:true}).click();
 await panel.getByLabel('Sua pergunta ou tese').fill('Vale manter, encerrar ou rolar uma opção da minha carteira?');
 await panel.getByRole('button',{name:'Analisar pergunta ou tese',exact:true}).click();
 await panel.getByRole('region',{name:'Esclarecimento necessário para a estratégia'}).getByText('Qual é o código exato da opção que deseja analisar?',{exact:true}).waitFor();
 await panel.getByText('Aguardando esclarecimento',{exact:false}).waitFor();
 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('A opção é PETRK376.');
 await panel.getByRole('button',{name:'Enviar continuação',exact:true}).click();
 await panel.getByRole('article',{name:'Análise 2'}).getByText('Deseja analisar toda a posição ou quantas unidades?',{exact:true}).waitFor();
 assert.equal(requests.at(-1).context.lab_conversation[0].response.lab_clarification.status,'NEEDS_CLARIFICATION');
 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('100 unidades.');
 await panel.getByRole('button',{name:'Enviar continuação',exact:true}).click();
 const identified=panel.getByRole('article',{name:'Análise 3'});
 await panel.getByText('Posição identificada · cálculos pendentes',{exact:false}).waitFor();
 await identified.getByText('100 unidades',{exact:true}).waitFor();
 assert.equal(requests.at(-1).context.lab_conversation[1].response.lab_position_selection.option_id,'PETRK376');
 assert.equal(await identified.getByText('Síntese concluída',{exact:false}).count(),0);
 await page.screenshot({path:resolve(out,'lab-position-selection-fixture.png'),animations:'disabled'});
 assert.deepEqual(errors,[]);
 console.log('PASS LAB-01/02/06: central response, no hidden defaults, continuation and reset (fixtures).');
}finally{await browser.close();}
