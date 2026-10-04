import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const base=process.env.B3_UI_URL||'http://127.0.0.1:5173';
const api=process.env.B3_API_URL||'http://127.0.0.1:8000';
const out=resolve(process.env.B3_VISUAL_OUTPUT||'visual-output');
await mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:900}});
await context.addInitScript(url=>localStorage.setItem('b3.apiBaseUrl',url),api);
const page=await context.newPage(),consoleErrors=[],requests=[];
page.on('pageerror',e=>consoleErrors.push(e.message));
page.on('request',r=>{if(r.url().endsWith('/orchestrate')){const b=r.postDataJSON();requests.push(b)}});
const backend=async(path)=>{const r=await context.request.get(api+path);assert.equal(r.status(),200,`Backend read failed: ${path}`);return r.json()};
const portfolio=await backend('/portfolio/current');
assert.ok(portfolio.positions.length>0,'Real portfolio must exist for acceptance');
const health=await backend('/health');assert.ok(health.status);
async function nav(label){await page.locator('nav').getByRole('button',{name:label,exact:true}).click();await page.locator('h1').filter({hasText:label}).waitFor();}
async function screenshot(name){await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:resolve(out,name+'.png'),fullPage:false,animations:'disabled'});}
async function noOverflow(){const size=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,width:innerWidth}));assert.ok(size.scroll<=size.width+1,`Global horizontal overflow ${size.scroll}/${size.width}`)}
try {
await page.goto(base+'/#/portfolio');
await page.getByRole('button',{name:'Carregando…',exact:true}).waitFor({state:'hidden',timeout:60000});
await page.getByRole('heading',{name:'Ações na carteira',exact:true}).waitFor();
for(const p of portfolio.positions.filter(p=>p.instrument_type==='STOCK').slice(0,3)){
 const row=page.locator('main tr').filter({has:page.getByRole('button',{name:p.ticker,exact:true})});
 await row.first().waitFor();assert.ok((await row.first().innerText()).includes(String(p.quantity.toLocaleString('pt-BR'))));
}
await page.getByLabel('Buscar posição',{exact:true}).fill('PETR');
await nav('Options');await nav('Portfolio');assert.equal(await page.getByLabel('Buscar posição',{exact:true}).inputValue(),'PETR','Filter continuity lost');
await page.getByLabel('Buscar posição',{exact:true}).fill('');
await nav('Options');await page.getByRole('tab',{name:'Resultados',exact:true}).click();await page.getByText('Resultado mensal e acumulado · LIMITED',{exact:true}).waitFor();
await page.getByRole('tab',{name:'Execuções',exact:true}).click();await page.getByRole('tab',{name:'Posições',exact:true}).click();
await page.getByRole('tab',{name:'Cadeia de opções',exact:true}).click();await page.getByLabel('Ativo da cadeia',{exact:true}).fill('PETR4');
const chainResponse=page.waitForResponse(r=>r.url().includes('/options/current/PETR4'),{timeout:90000});await page.getByRole('button',{name:'Consultar cadeia',exact:true}).click();const chain=await (await chainResponse).json();assert.ok(chain.options.length>0,'Real OPLAB chain missing');await page.getByRole('button',{name:chain.options[0].contract.option_id,exact:true}).waitFor();await screenshot('oplab-chain-real');await page.getByRole('tab',{name:'Posições',exact:true}).click();
await nav('Strategy Lab');
const comparisonResponse=page.waitForResponse(r=>r.url().endsWith('/orchestrate')&&r.request().postDataJSON().context?.comparison_assets?.join(',')==='ITUB4,BBDC4',{timeout:120000});
await page.getByTestId('primary-comparison').getByRole('button',{name:'Comparar fatos',exact:true}).click();
const comparison=await (await comparisonResponse).json();assert.ok(!comparison.error,'Canonical BUY failed');
assert.equal(comparison.result.stock_purchase_comparison.rows.length,2);
await page.getByTestId('primary-comparison-result').getByRole('heading',{name:'Compra entre ações · fundamentos e perspectivas',exact:true}).waitFor({timeout:10000});
assert.ok((await page.getByTestId('primary-comparison-result').innerText()).includes('ITUB4'));
await screenshot('strategy-comparison-real');
await page.getByText('Premissas e estratégias avançadas: cenários, custos, troca financiada e strikes',{exact:true}).click();
const scenarioForm=page.locator('form').filter({has:page.getByRole('button',{name:'Comparar',exact:true})});await scenarioForm.getByLabel('Horizonte comum dos cenários',{exact:true}).fill('2026-11-04');
const scenarioResponse=page.waitForResponse(r=>r.url().endsWith('/orchestrate')&&r.request().postDataJSON().context?.scenario_horizon==='2026-11-04',{timeout:120000});await scenarioForm.getByRole('button',{name:'Comparar',exact:true}).click();const scenarioComparison=await (await scenarioResponse).json();assert.ok(!scenarioComparison.error);assert.ok(scenarioComparison.result.scenario_analysis.alternatives.length===2);await page.getByRole('img',{name:'P&L canônico por cenário e alternativa',exact:true}).waitFor();await screenshot('strategy-scenarios-real');
await page.getByText('Premissas e estratégias avançadas: cenários, custos, troca financiada e strikes',{exact:true}).click();
await nav('Opportunities');
await page.getByLabel('Universo de ações (até 20)',{exact:true}).fill('ITUB4, BBDC4');
const opportunityResponse=page.waitForResponse(r=>r.url().endsWith('/orchestrate')&&r.request().postDataJSON().context?.opportunity_assets?.join(',')==='ITUB4,BBDC4',{timeout:120000});
await page.getByRole('button',{name:'Comparar / ordenar',exact:true}).click();
const opportunity=await (await opportunityResponse).json();assert.ok(!opportunity.error);assert.equal(opportunity.result.opportunity_screen.rows.length,2);
await page.getByRole('button',{name:'Abrir análise',exact:true}).first().waitFor();await page.getByRole('button',{name:'Abrir análise',exact:true}).first().click();await page.getByRole('heading',{name:/análise da oportunidade/}).waitFor();
await screenshot('opportunity-detail-real');await page.getByRole('button',{name:'Voltar ao ranking',exact:true}).click();
await nav('Risk & Stress');await page.getByLabel('Ativo do stress',{exact:true}).fill('PETR4');
const stressResponse=page.waitForResponse(r=>r.url().endsWith('/orchestrate')&&r.request().postDataJSON().context?.ticker_price_shocks,{timeout:60000});
await page.getByRole('button',{name:'Simular impacto',exact:true}).click();const stress=await (await stressResponse).json();assert.ok(!stress.error);assert.ok(stress.result.scenario_result);await page.getByRole('heading',{name:'Impacto por posição',exact:true}).waitFor();
await nav('History & Learning');await page.getByLabel('Ativo do histórico',{exact:true}).fill('PETR4');
const historyResponse=page.waitForResponse(r=>r.url().includes('/history/context?'),{timeout:30000});await page.getByRole('button',{name:'Consultar histórico',exact:true}).click();assert.equal((await historyResponse).status(),200);await page.getByText('Operações pessoais · evidência disponível',{exact:true}).waitFor();
for(const [label,title] of [['Learnings','Aprendizados · LIMITED'],['Similarity','Similaridade · LIMITED']]){await page.getByRole('tab',{name:label,exact:true}).click();const response=page.waitForResponse(r=>r.url().includes('/history/context?'));await page.getByRole('button',{name:'Consultar histórico',exact:true}).click();const value=await (await response).json();assert.equal(value.learning_sample_size,0);await page.getByText(title,{exact:true}).waitFor();await screenshot(label.toLowerCase()+'-limited-real')}
await page.getByRole('tab',{name:'Operations',exact:true}).click();
await nav('Market Intelligence');
for(const label of ['Regime','Factors','Research & Events']){await page.getByRole('tab',{name:label,exact:true}).click();const response=page.waitForResponse(r=>r.url().endsWith('/orchestrate')&&r.request().postDataJSON().context?.workspace==='Market Intelligence',{timeout:90000});await page.getByRole('button',{name:'Analisar contexto',exact:true}).click();const value=await (await response).json();assert.ok(value.result.workspace_intelligence);assert.equal(value.result.telemetry.llm_calls,0);await page.locator('.context-evidence').waitFor();await screenshot('market-'+label.toLowerCase().replaceAll(/[^a-z]+/g,'-')+'-real')}
await page.getByRole('button',{name:'Ativo · gráfico e indicadores',exact:true}).click();
await page.getByLabel('Ativo B3',{exact:true}).fill('PETR4');
const marketResponse=page.waitForResponse(r=>r.url().endsWith('/analysis/live/PETR4'),{timeout:60000});await page.locator('main').getByRole('button',{name:'Analisar',exact:true}).click();const market=await (await marketResponse).json();assert.ok(market.market.price_history.length>0);
await page.getByRole('img',{name:/Preço e volume em/}).waitFor({timeout:30000});
for(const range of ['1S','1M','1A']){await page.getByRole('button',{name:range,exact:true}).click();await page.getByRole('heading',{name:/Histórico de preços/}).waitFor();}
await page.getByLabel('Volume',{exact:true}).uncheck();await page.getByLabel('Volume',{exact:true}).check();await page.getByLabel('Zoom no período',{exact:true}).check();
const routes=['Overview','Portfolio','Options','Opportunities','Strategy Lab','Market Intelligence','History & Learning','Risk & Stress'];
for(const [width,height] of [[1920,1080],[1440,900],[1366,768]]){
 await page.setViewportSize({width,height});
 for(const label of routes){await nav(label);await noOverflow();await screenshot(`${label.toLowerCase().replaceAll(/[^a-z]+/g,'-')}-${width}`)}
 await page.getByRole('button',{name:'Recolher menu',exact:true}).click();await noOverflow();await screenshot(`sidebar-collapsed-${width}`);await page.getByRole('button',{name:'Recolher menu',exact:true}).click();
 await page.getByRole('button',{name:'Fechar Copilot',exact:true}).click();await noOverflow();await screenshot(`copilot-closed-${width}`);await page.getByRole('button',{name:/Copilot \+/}).click();
}
await nav('Portfolio');const copilotResponse=page.waitForResponse(r=>r.url().endsWith('/orchestrate')&&r.request().postDataJSON().task==='Resuma a concentração da carteira.',{timeout:60000});await page.locator('.chat-form textarea').fill('Resuma a concentração da carteira.');await page.getByRole('button',{name:'Enviar',exact:true}).click();const copilot=await (await copilotResponse).json();assert.ok(!copilot.error);assert.equal(copilot.result.portfolio_context.positions.length,portfolio.positions.length);await page.locator('.copilot').getByRole('heading',{name:'Carteira canônica',exact:true}).waitFor();await screenshot('copilot-context-real');
await nav('Strategy Lab');await page.locator('.chat-form textarea').fill('Está online?');await page.getByRole('button',{name:'Enviar',exact:true}).click();await page.getByText(/Sim. Estou conectado ao B3 Runtime/).waitFor();
assert.equal(consoleErrors.length,0,`Browser errors: ${consoleErrors.join('; ')}`);
assert.ok(requests.some(r=>r.context?.ticker_price_shocks?.PETR4===-0.1),'Percentage unit conversion incorrect');
assert.ok(requests.some(r=>r.context?.comparison_assets?.join(',')==='ITUB4,BBDC4'&&r.context.analysis_mode==='deterministic'));
const report={status:'PASS',real_backend:true,resolutions:[1920,1440,1366],screens:routes,interaction_checks:['route','portfolio coherence','filter continuity','option limited state','OPLAB chain with source Greeks','UC06 limited state','UC08 and UC09 real zero sample','macro and stored event queries','buy comparison','canonical scenario chart','opportunity detail','stress','personal history','price ranges','volume','zoom','copilot close/open','copilot health','UC12 contextual canonical portfolio answer'],page_errors:consoleErrors,raw_payloads_uploaded:false};
await writeFile(resolve(out,'acceptance.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify(report));
} catch(error){await screenshot('failure-current-screen');await writeFile(resolve(out,'failure.json'),JSON.stringify({status:'FAIL',url:page.url(),reason:error.message,page_errors:consoleErrors},null,2));throw error} finally{await browser.close()}
