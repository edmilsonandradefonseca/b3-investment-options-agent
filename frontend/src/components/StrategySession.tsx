import {useRef, useState} from 'react';
import {b3Api} from '../api/client';
import type {OrchestrateResponse} from '../api/contracts';
import AnalysisOutput from './AnalysisOutput';

type Turn = {question:string; response:OrchestrateResponse|null; error?:string; at:string; portfolioRevision:string|null};
const examples = ['Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4?', 'Acredito que PETR4 pode cair. Quais evidências sustentam ou contradizem essa tese?', 'Vale manter, encerrar ou rolar uma opção da minha carteira?'];

// LAB-01/02/06: independent central session; never inject structured-form defaults.
export default function StrategySession({researchMode='stored_first',portfolioRevision=null}:{researchMode?:string;portfolioRevision?:string|null}){
 const [question,setQuestion]=useState('');
 const [turns,setTurns]=useState<Turn[]>([]);
 const [status,setStatus]=useState<'idle'|'running'|'done'|'clarification'|'error'>('idle');
 const inFlight=useRef(false);
 const [retryQuestion,setRetryQuestion]=useState('');
 async function analyze(text=question){
  const task=text.trim();
  if(!task||inFlight.current)return;
  inFlight.current=true;setStatus('running');setRetryQuestion(task);
  const index=turns.length;
  const previous=turns.filter(t=>t.response&&!t.error&&t.portfolioRevision===portfolioRevision);
  setTurns(v=>[...v,{question:task,response:null,at:new Date().toISOString(),portfolioRevision}]);
  setQuestion('');
  try{
   const response=await b3Api.orchestrate({task,ticker:null,context:{
    workspace:'Strategy Lab',research_mode:researchMode,
    lab_conversation:previous.map(t=>({question:t.question,response:{
     summary:t.response?.result.summary,
     lab_clarification:t.response?.result.lab_clarification,
     proposal:t.response?.result.proposal??t.response?.result.decision_proposal,
     synthesis:t.response?.result.synthesis,
     stock_purchase_comparison:t.response?.result.stock_purchase_comparison,
     scenario_analysis:t.response?.result.scenario_analysis,
     as_of:t.response?.result.as_of,
     sources:t.response?.sources,
    }})),
    lab_request_kind:previous.length?'follow_up':'new_analysis',
    response_guidance:'Responda primeiro em linguagem natural: avaliação, evidências favoráveis e contrárias, riscos e condições de mudança. Trate teses como hipóteses. Use cálculos determinísticos para números; peça somente esclarecimentos indispensáveis. Considere a carteira completa. A conversa anterior é contexto histórico, não cotação atual.',
   }});
   const failed=Boolean(response.error)||response.result.derived_synthesis_status==='FAILED';
   setTurns(v=>v.map((t,i)=>i===index?{...t,response,error:failed?'Não foi possível concluir a síntese. Os dados recebidos permanecem disponíveis.':undefined}:t));
   setStatus(failed?'error':response.status==='NEEDS_CLARIFICATION'?'clarification':'done');
  }catch{
   setTurns(v=>v.map((t,i)=>i===index?{...t,error:'Não foi possível concluir a análise. Tente novamente; as respostas anteriores foram preservadas.'}:t));
   setStatus('error');
  }finally{inFlight.current=false;}
 }
 const label={idle:'Aguardando',running:'Em processamento · avaliando dados e evidências',done:'Concluído',clarification:'Aguardando identificação do contrato',error:'Problema na análise'}[status];
 return <section className="panel strategy-session" aria-label="Pergunta e análise do Strategy Lab">
  <div className="section-head"><h2>O que você deseja analisar?</h2><div className="action-row"><span role="status" aria-live="polite"><span aria-hidden="true" style={{color:{idle:'#94a3b8',running:'#eab308',done:'#22c55e',clarification:'#94a3b8',error:'#ef4444'}[status]}}>● </span>{label}</span><button type="button" disabled={status==='running'} onClick={()=>{setTurns([]);setQuestion('');setRetryQuestion('');setStatus('idle')}}>Nova análise</button></div></div>
  <p>Escreva uma pergunta, uma tese ou as alternativas que deseja comparar.</p>
  {!turns.length&&<div className="workspace-tabs">{examples.map(text=><button key={text} type="button" disabled={status==='running'} onClick={()=>setQuestion(text)}>{text}</button>)}</div>}
  {turns.map((turn,i)=><article className="panel" key={i} aria-label={`Análise ${i+1}`}>
   <h3>{i+1}. {turn.question}</h3><small>Solicitada em {new Date(turn.at).toLocaleString('pt-BR',{timeZone:'America/Sao_Paulo'})} · horário das fontes no resultado</small>
   {turn.portfolioRevision!==portfolioRevision&&<p role="status">A carteira mudou desde esta análise. Esta resposta mantém o contexto anterior; inicie uma nova análise para reavaliar a posição atual.</p>}
   <h3>Análise do agente B3</h3>
   {turn.error&&<p role="alert">{turn.error}</p>}
   {turn.response?<AnalysisOutput data={turn.response}/>:!turn.error&&<p role="status">Avaliando sua pergunta com os dados e evidências disponíveis…</p>}
  </article>)}
  <form onSubmit={e=>{e.preventDefault();void analyze()}}>
   <label htmlFor="strategy-thesis">{turns.length?'Ajustar ou aprofundar esta análise':'Sua pergunta ou tese'}</label>
   <textarea id="strategy-thesis" value={question} onChange={e=>setQuestion(e.target.value)} rows={4} required disabled={status==='running'} placeholder="Descreva seu objetivo, a tese ou as alternativas…" style={{display:'block',width:'100%',boxSizing:'border-box',margin:'12px 0'}}/>
   <div className="toolbar"><button disabled={status==='running'||!question.trim()}>{turns.length?'Enviar continuação':'Analisar pergunta ou tese'}</button>
   
   {status==='error'&&<button type="button" onClick={()=>void analyze(retryQuestion)}>Tentar novamente</button>}
   </div>
  </form>
 </section>;
}
