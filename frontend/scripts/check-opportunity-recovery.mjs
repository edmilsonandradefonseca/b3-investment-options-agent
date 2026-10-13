// Fixture-only regression: a failed view must observe a later scheduled success.
import {chromium,expect} from '@playwright/test';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
try{
 const page=await browser.newPage();
 let phase='failed', searches=0, latestReads=0;
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.addInitScript(()=>{
  localStorage.setItem('b3.apiBaseUrl','http://127.0.0.1:8000');
  const interval=window.setInterval.bind(window);
  window.setInterval=(fn,ms,...args)=>interval(fn,Math.min(ms,200),...args);
 });
 const old={status:'FAILED',run_id:'old',started_at:'2026-10-13T14:40:00Z',finished_at:'2026-10-13T14:41:00Z',error:'HTTPException',result_available:true};
 const completed={status:'COMPLETED',run_id:'new',started_at:'2026-10-13T15:00:00Z',finished_at:'2026-10-13T15:02:00Z',error:null,result_available:true};
 await page.route('http://127.0.0.1:8000/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname;
  if(req.method()==='OPTIONS')return route.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type'}});
  let data={};
  if(path==='/health')data={status:'ok',llm_enabled:true};
  else if(path==='/opportunities/status')data=phase==='failed'?old:completed;
  else if(path==='/opportunities/latest'){
   latestReads++;
   data={status:'AVAILABLE',run_id:phase==='failed'?'old':'new',generated_at:completed.finished_at,response:{status:'PASS',result:{summary:phase==='failed'?'fixture previous':'fixture recovered',derived_synthesis_status:'COMPLETED'},sources:[],audit:[],error:null}};
  }else if(path==='/portfolio/current')return route.fulfill({status:503,json:{detail:'fixture: no portfolio'},headers:{'Access-Control-Allow-Origin':'*'}});
  else if(path==='/orchestrate'){searches++;data={status:'COMPLETED',result:{},sources:[],audit:[],error:null};}
  else if(path.includes('transactions'))data=[];
  else if(path.includes('ledger'))data={operations:[]};
  else if(path.includes('options'))data={options:[]};
  await route.fulfill({json:data,headers:{'Access-Control-Allow-Origin':'*'}});
 });
 await page.goto((process.env.B3_UI_URL||'http://127.0.0.1:4173')+'/#opportunities');
 const status=page.locator('.opportunity-run-status');
 await expect(status).toContainText('Falha na nova busca');
 phase='completed';
 await expect(status).toContainText('Busca concluída',{timeout:10000});
 await expect(status).not.toContainText('HTTPException');
 await expect(page.locator('.opportunity-decision__summary')).toBeVisible();
 const reads=latestReads;
 await page.waitForTimeout(700);
 assert.equal(latestReads,reads,'Completed result must not be fetched on every poll');
 assert.equal(searches,0,'Status synchronization must not request a new analysis');
 assert.deepEqual(errors,[]);
 console.log('OPPORTUNITIES_STALE_FAILURE_RECOVERY=PASS; fixture only; no analysis requested');
}finally{await browser.close();}
