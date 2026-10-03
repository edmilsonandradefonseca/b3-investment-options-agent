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
    proposal:{action:'WAIT',subject_id:'A versus B',thesis:'Evidence required',rationale:'Conditional decision',confidence:'UNKNOWN',capital_impact:'Missing cash evidence',opportunity_cost:'Foregone alternative',invalidation_conditions:['Verified new evidence'],evidence_refs:['canonical:1']},
    synthesis:{conflicts:['Conflicting evidence'],agreements:[],uncertainties:[],evidence_gaps:[]},
    market_agent_analysis:{summary:'Market view',findings:['Material finding'],risks:['Specific market risk'],source_refs:['provider:1'],evidence_refs:[]},
    risk_validation:{status:'FAIL',reasons:['Capital not established']},
  }};
  const html = renderToStaticMarkup(createElement(AnalysisOutput,{data}));
  // Ignore the debug JSON: these facts must reach the human-facing output.
  const visible = html.split('<details class="technical-output">')[0];
  for (const value of ['Missing cash evidence','Foregone alternative','Verified new evidence','Conflicting evidence','Material finding','Specific market risk','Capital not established','provider:1']) {
    assert.ok(visible.includes(value), `Decision content lost before render: ${value}`);
  }
  console.log('Decision rendering: PASS (human-facing evidence and tradeoffs)');
} finally {
  await rm(directory,{recursive:true,force:true});
}
