import { build } from 'vite';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import assert from 'node:assert/strict';

const directory = await mkdtemp(join(process.cwd(), '.decision-render-'));
try {
  const output = join(directory, 'output.mjs');
  await build({logLevel:'error',build:{ssr:'src/components/AnalysisOutput.tsx',outDir:directory,emptyOutDir:false,rollupOptions:{output:{entryFileNames:'output.mjs'}}}});
  const { default: AnalysisOutput } = await import(pathToFileURL(output).href);
  const data = {status:'PASS', error:null, sources:[], audit:[], result:{
    workspace_intelligence:{workspace:'Strategy Lab'},
    proposal:{alternative_assessments:[{alternative_id:'A',supporting_evidence:['Verified supporting evidence'],contradicting_evidence:['Verified contrary evidence'],decision_implications:['Alternative specific tradeoff'],unknowns:['Missing comparable valuation'],evidence_refs:['canonical:1']}],action:'WAIT',subject_id:'A versus B',thesis:'Evidence required',rationale:'Conditional decision',confidence:'UNKNOWN',capital_impact:'Missing cash evidence',opportunity_cost:'Foregone alternative',invalidation_conditions:['Verified new evidence'],evidence_refs:['canonical:1']},
    synthesis:{conflicts:['Conflicting evidence'],agreements:[],uncertainties:[],evidence_gaps:[]},
    market_agent_analysis:{summary:'Market view',findings:['Material finding'],risks:['Specific market risk'],source_refs:['provider:1'],evidence_refs:[]},
    risk_validation:{status:'FAIL',reasons:['Capital not established']},
  }};
  const html = renderToStaticMarkup(createElement(AnalysisOutput,{data}));
  // Ignore the debug JSON: these facts must reach the human-facing output.
  const visible = html.split('<details class="technical-output">')[0];
  for (const value of ['Verified supporting evidence','Verified contrary evidence','Alternative specific tradeoff','Missing comparable valuation','Missing cash evidence','Foregone alternative','Verified new evidence','Conflicting evidence','Material finding','Specific market risk','Capital not established','provider:1']) {
    assert.ok(visible.includes(value), `Decision content lost before render: ${value}`);
  }
  const screenData={status:'COMPLETED',error:null,sources:[],audit:[],result:{workspace_intelligence:{workspace:'Opportunities'},opportunity_screen:{status:'PARTIAL_COMPARABLE_UNIVERSE',objective:'LOWEST_REALIZED_VOLATILITY_60D',reference_window_start:'2026-07-01',reference_window_end:'2026-10-02',rows:[{ticker:'ITUB4',rank:1,portfolio:{held:null,stock_quantity:null},volatility_60d:null,liquidity_proxy_20d:null,exclusions:['NONCOMPARABLE_OBSERVATION_WINDOW'],source_refs:['source:screen'],ranking_evidence_ref:'quant:screen'}]}}};
  const screenHTML=renderToStaticMarkup(createElement(AnalysisOutput,{data:screenData})).split('<details class="technical-output">')[0];
  assert.ok(screenHTML.includes('UNKNOWN'));
  assert.ok(screenHTML.includes('Janela de observações diferente'));
  assert.ok(screenHTML.includes('source:screen'));
  assert.ok(!screenHTML.includes('Sem ranking disponível'));
  const buyData={...data,result:{stock_purchase_comparison:{rows:[{alternative_id:'BUY:A',ticker:'ITUB4',source_refs:['verified-buy-source'],fundamental_metrics:{priceEarnings:{value:9,unit:'ratio',report_date:'2026-09-30',period_type:'TTM',source:'qualified-fundamental',quality_status:'WARNING'}},observed_risk:{},excluded_metrics:[],dividends:{collection_status:'READ_OK',events:[{payment_type:'JCP',gross_amount_per_share_brl:1,source:'issuer-source',source_record_id:'issuer:1',record_date:'2026-10-05',payment_date:'2026-10-30',new_purchase_entitlement:'CONDITIONAL_FUTURE_RECORD_DATE'}],limitations:['Dividend entitlement is conditional']} }],limitations:['No qualified forward dividend forecast']}}};
  const buyHTML=renderToStaticMarkup(createElement(AnalysisOutput,{data:buyData})).split('<details class="technical-output">')[0];
  for(const value of ['Compra entre ações','ITUB4','verified-buy-source','qualified-fundamental','TTM','No qualified forward dividend forecast','UNKNOWN','issuer-source','issuer:1','2026-10-30','Condicional']) assert.ok(buyHTML.includes(value),`BUY comparison lost: ${value}`);
  console.log('Decision rendering: PASS (human-facing evidence and tradeoffs)');
} finally {
  await rm(directory,{recursive:true,force:true});
}
