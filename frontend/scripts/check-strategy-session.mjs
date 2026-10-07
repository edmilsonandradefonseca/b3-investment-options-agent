// LAB-01/02/06, WS-05: browser contract test with explicit fixtures, not live acceptance.
import {chromium,expect} from '@playwright/test';
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
  if(req.url().includes('/analysis/live/')){
   const ticker=decodeURIComponent(req.url().split('/analysis/live/')[1].split('?')[0]);
   const base=ticker==='ITUB4'?30:ticker==='BBDC4'?20:10;
   const price_history=[0,1,2].map((offset)=>({ticker,observation_timestamp:['2026-10-01T12:00:00+00:00','2026-10-05T12:00:00+00:00','2026-10-07T12:00:00+00:00'][offset],available_timestamp:'2026-10-07T12:01:00+00:00',source:'fixture:history',source_record_id:ticker+':'+offset,open:base+offset,high:base+offset+1,low:base+offset-1,close:base+offset,adjusted_close:null,volume:1000,currency:'BRL'}));
   const latest=price_history.at(-1);
   return route.fulfill({json:{ticker,as_of:'2026-10-07T12:01:00+00:00',source_refs:['fixture:history'],market:{history_count:price_history.length,price_history,current_quote:null,current_quote_status:'UNAVAILABLE',history_latest:latest,latest},options:{contract_count:0,quote_count:0,contracts:[],quotes:[],analysis:{puts:[],calls:[],source_refs:[],quality_status:'WARNING',assumptions:null}}},headers:{'Access-Control-Allow-Origin':'*'}});
  }
  if(req.url().endsWith('/orchestrate')&&body?.context?.workspace==='Strategy Lab'){
   requests.push(body);
   if(body.task==='Vale manter, encerrar ou rolar uma opção da minha carteira?')return route.fulfill({json:{status:'NEEDS_CLARIFICATION',result:{lab_clarification:{status:'NEEDS_CLARIFICATION',question:'Qual é o código exato da opção que deseja analisar?',reason:'Informe o contrato.'},derived_synthesis_status:'NOT_REQUESTED'},sources:[],audit:[],error:null},headers:{'Access-Control-Allow-Origin':'*'}});
   if(body.task==='Compare manter, encerrar e rolar.'){
    const result={lab_position_selection:{option_id:'PETRK376',status:'POSITION_AND_QUANTITY_IDENTIFIED',side:'SHORT',snapshot_as_of:'2026-10-06',available_quantity_units:2500,selected_quantity_units:100,position:{underlying_ticker:'PETR4',option_type:'CALL',strike:37.6,expiration_date:'2026-11-20',source_ref:'fixture:current-snapshot'}},lab_clarification:{status:'NEEDS_CLARIFICATION',question:'Escolha o código exato do novo contrato de rolagem entre os contratos elegíveis abaixo.',reason:'Nenhum destino foi escolhido.'},lab_roll_candidates:[{option_id:'PETRK400',option_type:'CALL',strike:40,expiration_date:'2026-12-18',executable_side:'BID',executable_quote_brl:1.5,source:'OPLAB',quote_as_of:'2026-10-06T14:00:00+00:00'}],summary:'Selecione o contrato de destino.'};
    return route.fulfill({json:{status:'NEEDS_CLARIFICATION',result,sources:[],audit:[],error:null},headers:{'Access-Control-Allow-Origin':'*'}});
   }
   if(body.task==='PETRK400'){
    const result={policy_version:'lab-option-management-v1',summary:'Comparação determinística de manter, encerrar e rolar.',alternatives:[{alternative_id:'KEEP',label:'Manter posição',incremental_gross_cash_flow_brl:0,transaction_costs_brl:0,incremental_net_cash_flow_brl:0,accumulated_realized_pnl_brl:null,legs:[]},{alternative_id:'CLOSE',label:'Encerrar quantidade selecionada',incremental_gross_cash_flow_brl:-1100,transaction_costs_brl:25,incremental_net_cash_flow_brl:-1125,accumulated_realized_pnl_brl:null,legs:[{contract_id:'PETRK376',option_type:'CALL',strike:37.6,expiration_date:'2026-11-20',trade_side:'BUY',quantity_contract_units:100,contract_multiplier:100,price_field:'ask',price_brl_per_underlying_unit:0.11,gross_incremental_cash_flow_brl:-1100,source:'OPLAB',quote_as_of:'2026-10-06T14:00:00+00:00'}]},{alternative_id:'ROLL',label:'Rolar para o contrato selecionado',incremental_gross_cash_flow_brl:-950,transaction_costs_brl:50,incremental_net_cash_flow_brl:-1000,accumulated_realized_pnl_brl:null,legs:[{contract_id:'PETRK376',option_type:'CALL',strike:37.6,expiration_date:'2026-11-20',trade_side:'BUY',quantity_contract_units:100,contract_multiplier:100,price_field:'ask',price_brl_per_underlying_unit:0.11,gross_incremental_cash_flow_brl:-1100,source:'OPLAB',quote_as_of:'2026-10-06T14:00:00+00:00'},{contract_id:'PETRK400',option_type:'CALL',strike:40,expiration_date:'2026-12-18',trade_side:'SELL',quantity_contract_units:100,contract_multiplier:100,price_field:'bid',price_brl_per_underlying_unit:0.015,gross_incremental_cash_flow_brl:150,source:'OPLAB',quote_as_of:'2026-10-06T14:00:00+00:00'}]}],portfolio_before:{cash_status:'UNKNOWN',positions:[]},portfolio_after_close:{positions:[],cash_after_brl:null},portfolio_after_roll:{positions:[],cash_after_brl:null},comparison:{ranking:'NOT_APPLIED',reason:'Sem ranking.'},limitations:['Custos parciais.']};
    return route.fulfill({json:{status:'COMPLETED',result,sources:[],audit:[],error:null},headers:{'Access-Control-Allow-Origin':'*'}});
   }
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
 const submit=async()=>{
  const input=page.locator('#strategy-thesis');
  const button=page.getByRole('button',{name:/Analisar pergunta ou tese|Enviar continuação/}).last();
  console.log('STRATEGY_FIELDS_AFTER_FILL', JSON.stringify(await page.locator('textarea').evaluateAll(items => items.map(item => ({id:item.id,value:item.value,label:item.labels?.[0]?.textContent,visible:!!(item.offsetWidth||item.offsetHeight)})))));
  await expect(input).toHaveValue(/\S/);
  await expect(button).toBeVisible();
  await expect(button).toBeEnabled();
  await button.click();
 };
 await panel.getByLabel('Sua pergunta ou tese').fill('Avalie minha tese sobre PETR4.');
 console.log('STRATEGY_PAGE_DEBUG', JSON.stringify({
  url: page.url(),
  regionCount: await panel.count(),
  textareas: await page.locator('textarea').evaluateAll(items => items.map(item => ({id:item.id,value:item.value,visible:!!(item.offsetWidth||item.offsetHeight)}))),
  labels: await page.locator('label').allTextContents(),
  body: (await page.locator('body').innerText()).slice(0,2500),
  pageErrors: errors,
 }));
 await submit();
 await panel.getByText('Resposta de fixture: tese exige verificar premissas.',{exact:true}).waitFor();
 const firstChart=panel.getByRole('region',{name:'Gráfico histórico do Strategy Lab'});
 await firstChart.getByRole('button',{name:'1 semana',exact:true}).waitFor();
 await firstChart.getByRole('img',{name:'Histórico de PETR4'}).waitFor();
 const oneYear=firstChart.getByRole('button',{name:'1 ano',exact:true});
 await oneYear.click();
 assert.equal(await oneYear.getAttribute('aria-pressed'),'true');
 assert.equal(requests.length,1);assert.equal(requests[0].ticker,null);
 assert.equal(requests[0].context.comparison_assets,undefined);
 assert.equal(requests[0].context.analysis_mode,undefined);
 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('E se cair 5%?');
 await submit();
 await panel.getByRole('article',{name:'Análise 2'}).getByText('Resposta de fixture: tese exige verificar premissas.',{exact:true}).waitFor();
 assert.equal(requests[1].context.lab_conversation[0].question,'Avalie minha tese sobre PETR4.');
 const out=resolve(process.env.B3_VISUAL_OUTPUT||'visual-output');await mkdir(out,{recursive:true});
 for(const [width,height] of [[1440,900],[1180,720]]){await page.setViewportSize({width,height});await page.screenshot({path:resolve(out,`lab-central-fixture-${width}.png`),animations:'disabled'});}

 await panel.getByRole('button',{name:'Nova análise',exact:true}).click();
 assert.equal(await panel.locator('article').count(),0);
 await panel.getByLabel('Sua pergunta ou tese').fill('Nova tese sobre VALE3.');
 await submit();
 await panel.getByText('Resposta de fixture: tese exige verificar premissas.',{exact:true}).waitFor();
 assert.equal(requests[2].context.lab_conversation.length,0);
 await panel.getByRole('button',{name:'Nova análise',exact:true}).click();
 await panel.getByLabel('Sua pergunta ou tese').fill('Vale manter, encerrar ou rolar uma opção da minha carteira?');
 await submit();
 await panel.getByRole('region',{name:'Esclarecimento necessário para a estratégia'}).getByText('Qual é o código exato da opção que deseja analisar?',{exact:true}).waitFor();
 await panel.getByText('Aguardando esclarecimento',{exact:false}).waitFor();
 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('A opção é PETRK376.');
 await submit();
 await panel.getByRole('article',{name:'Análise 2'}).getByText('Deseja analisar toda a posição ou quantas unidades?',{exact:true}).waitFor();
 assert.equal(requests.at(-1).context.lab_conversation[0].response.lab_clarification.status,'NEEDS_CLARIFICATION');
 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('100 unidades.');
 await submit();
 const identified=panel.getByRole('article',{name:'Análise 3'});
 await panel.getByText('Posição identificada · cálculos pendentes',{exact:false}).waitFor();
 await identified.getByText('100 unidades',{exact:true}).waitFor();
 assert.equal(requests.at(-1).context.lab_conversation[1].response.lab_position_selection.option_id,'PETRK376');
 assert.equal(await identified.getByText('Síntese concluída',{exact:false}).count(),0);
 await page.screenshot({path:resolve(out,'lab-position-selection-fixture.png'),animations:'disabled'});

 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('Compare manter, encerrar e rolar.');
 await submit();
 const candidates=panel.getByRole('article',{name:'Análise 4'});
 await candidates.getByText('PETRK400',{exact:false}).waitFor();
 await panel.getByLabel('Ajustar ou aprofundar esta análise').fill('PETRK400');
 await submit();
 const comparison=panel.getByRole('article',{name:'Análise 5'});
 await comparison.getByRole('region',{name:'Comparação de manter, encerrar e rolar no Strategy Lab'}).waitFor();
 const priorTurns=requests.at(-1).context.lab_conversation;
 const rollTurn=[...priorTurns].reverse().find(turn=>turn.response?.lab_roll_candidates?.some(candidate=>candidate.option_id==='PETRK400'));
 assert.ok(rollTurn,`Selected roll candidate was not carried into follow-up (${priorTurns.length} prior turns)`);
 assert.equal(rollTurn.response.lab_position_selection?.status,'POSITION_AND_QUANTITY_IDENTIFIED');
 await comparison.getByText('Fluxos incrementais brutos; não representam lucro ou retorno esperado',{exact:true}).waitFor();
 assert.equal(await comparison.getByText('UNKNOWN · histórico de abertura/custos',{exact:false}).count(),3);
 await page.screenshot({path:resolve(out,'lab-management-comparison-fixture.png'),animations:'disabled'});

 await panel.getByRole('button',{name:'Nova análise',exact:true}).click();
 await panel.getByLabel('Sua pergunta ou tese').fill('Compare ITUB4 e BBDC4.');
 await submit();
 await panel.getByText('Resposta de fixture: tese exige verificar premissas.',{exact:true}).last().waitFor();
 const comparisonChart=panel.getByRole('region',{name:'Gráfico histórico do Strategy Lab'}).last();
 await comparisonChart.getByRole('img',{name:'Histórico de ITUB4 e BBDC4'}).waitFor();
 assert.equal(await comparisonChart.locator('.recharts-line-curve').count(),2);
 assert.deepEqual(errors,[]);
 console.log('PASS LAB-01/02/03/04/05/06/07: clarification, current position, exact roll choice, three alternatives and provenance (fixtures).');
}finally{await browser.close();}
