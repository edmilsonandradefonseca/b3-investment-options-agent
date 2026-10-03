import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react';
import { b3Api, getApiBaseUrl, setApiBaseUrl } from './api/client';
import OptionsWorkspace from './OptionsWorkspace';
import AnalysisOutput from './components/AnalysisOutput';
import PersonalHistory from './components/PersonalHistory';
import type { CapitalProfile, PortfolioSnapshot, BrokerageOperation, PilotAnalysis, OrchestrateResponse, TransactionResponse, LiveAnalysisResponse, ResearchNewsResponse, FundamentalsResponse, CurrentOptionRow } from './api/contracts';

type Page = 'Portfolio'|'Options'|'Opportunities'|'Strategy Lab'|'Market Intelligence';
const pages: Page[] = ['Portfolio','Options','Opportunities','Strategy Lab','Market Intelligence'];
const dashboardFastPathUseCases: Partial<Record<Page, string[]>> = {
  Portfolio: ['UC-01'],
  Options: ['UC-02'],
};
const brl = (n?: number|null) => n == null ? 'Indisponível' : new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n);
const when = (s?:string|null) => s ? new Date(s).toLocaleString('pt-BR') : 'Indisponível';
const err = (e:unknown) => e instanceof Error ? e.message : String(e);
const optionTypeForStrategy=(strategy:string):'PUT'|'CALL'|null=>
 strategy==='Vender PUT'?'PUT':strategy==='Vender CALL coberta'?'CALL':null;
function HistoryChart({records}:{records:LiveAnalysisResponse['market']['history_latest'][]}){
 if(records.length<2)return <p className="muted">Histórico insuficiente para desenhar a série.</p>;
 const width=720,height=220,pad=24;
 const values=records.map(row=>row.adjusted_close??row.close);
 const low=Math.min(...values),high=Math.max(...values),span=high-low||1;
 const points=values.map((value,index)=>`${pad+index*(width-pad*2)/(values.length-1)},${height-pad-(value-low)*(height-pad*2)/span}`).join(' ');
 return <div className="price-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Histórico de preços com ${records.length} pregões`}><line x1={pad} y1={pad} x2={width-pad} y2={pad} className="chart-grid"/><line x1={pad} y1={height/2} x2={width-pad} y2={height/2} className="chart-grid"/><line x1={pad} y1={height-pad} x2={width-pad} y2={height-pad} className="chart-grid"/><polyline points={points} className="chart-line"/><text x={pad} y={14}>{brl(high)}</text><text x={pad} y={height-4}>{brl(low)}</text></svg><div className="chart-dates"><span>{when(records[0].observation_timestamp)}</span><span>{when(records[records.length-1].observation_timestamp)}</span></div></div>;
}
function fundamentalValue(metric: FundamentalsResponse["metrics"][number]): string {
 if(metric.unit==='BRL'||metric.unit?.endsWith('/share'))return brl(metric.value);
 const value=new Intl.NumberFormat('pt-BR',{maximumFractionDigits:4}).format(metric.value);
 return metric.unit?value+' '+metric.unit:value;
}
function eventText(event:Record<string,unknown>,...keys:string[]):string{
 for(const key of keys){const value=event[key];if(typeof value==='string'&&value.trim())return value}
 return '';
}
function eventUrl(event:Record<string,unknown>):string{
 const value=eventText(event,'url','source_ref','source_url');
 return value.startsWith('https://')||value.startsWith('http://')?value:'';
}
function isOperationalStatusQuestion(task:string){
 const normalized=task.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9 ]/g,' ').replace(/\s+/g,' ').trim();
 return /^(vc |voce |copilot |sistema )?(esta|ta) (on|online|conectado|funcionando)$/.test(normalized)
   || /^(status|status do sistema|esta conectado|esta funcionando)$/.test(normalized);
}
export default function App(){
 const inspectionSequence=useRef(0);
 const [researchMode,setResearchMode]=useState("stored_first");
 const [opportunityAssets,setOpportunityAssets]=useState('VALE3, RENT3, VIVT3, BBAS3');
 const [opportunityObjective,setOpportunityObjective]=useState('COMPARE_ONLY');
 const [includePortfolioStocks,setIncludePortfolioStocks]=useState(false);
 const [personalHistory,setPersonalHistory]=useState<Record<string,unknown>|null>(null);
 const [page,setPage]=useState<Page>('Portfolio'),[online,setOnline]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const [portfolio,setPortfolio]=useState<PortfolioSnapshot|null>(null),[capital,setCapital]=useState<CapitalProfile|null>(null),[tx,setTx]=useState<TransactionResponse[]>([]);
 const [brokerage,setBrokerage]=useState<BrokerageOperation[]>([]),[ledgerAvailable,setLedgerAvailable]=useState(false);
 const [url,setUrl]=useState(getApiBaseUrl()),[settings,setSettings]=useState(false),[capitalEdit,setCapitalEdit]=useState(false),[available,setAvailable]=useState(''),[reserve,setReserve]=useState('');
 const [ticker,setTicker]=useState(''),[asset,setAsset]=useState(''),[filter,setFilter]=useState(''),[analysis,setAnalysis]=useState<OrchestrateResponse|null>(null);
 const [live,setLive]=useState<LiveAnalysisResponse|null>(null),[news,setNews]=useState<ResearchNewsResponse|null>(null),[newsError,setNewsError]=useState(''),[fundamentals,setFundamentals]=useState<FundamentalsResponse|null>(null),[fundamentalsError,setFundamentalsError]=useState(''),[pilot,setPilot]=useState<PilotAnalysis|null>(null),[horizon,setHorizon]=useState('1M'),[assetView,setAssetView]=useState(false);
 const [question,setQuestion]=useState(''),[chat,setChat]=useState<{q:string;r:OrchestrateResponse|null;error?:string}[]>([]),[batch,setBatch]=useState<string>('');
 const [left,setLeft]=useState(''),[right,setRight]=useState(''),[strategyA,setStrategyA]=useState('Comprar ação'),[strategyB,setStrategyB]=useState('Vender PUT'),[amount,setAmount]=useState('');
 const [putPairObjective,setPutPairObjective]=useState('COMPARE_ONLY');
 const [fundedQuantity,setFundedQuantity]=useState('100'),[fundedFees,setFundedFees]=useState(''),[fundedTaxes,setFundedTaxes]=useState('');
 const [scenarioHorizon,setScenarioHorizon]=useState(''),[scenarioShocks,setScenarioShocks]=useState('-10, 0, 10'),[scenarioObjective,setScenarioObjective]=useState('COMPARE_ONLY');
 const [optionA,setOptionA]=useState(''),[optionB,setOptionB]=useState(''),[optionRowsA,setOptionRowsA]=useState<CurrentOptionRow[]>([]),[optionRowsB,setOptionRowsB]=useState<CurrentOptionRow[]>([]);
 const [putChainExpiry,setPutChainExpiry]=useState(''),[putCandidateIds,setPutCandidateIds]=useState<string[]>([]);
 async function load(){setBusy(true);try{await b3Api.health();setOnline(true);const [p,c,t,l]=await Promise.allSettled([b3Api.portfolio(),b3Api.capital(),b3Api.listTransactions(500),b3Api.optionLedger()]);if(p.status==='fulfilled')setPortfolio(p.value);if(c.status==='fulfilled'){setCapital(c.value);setAvailable(String(c.value.available_capital??''));setReserve(String(c.value.minimum_reserve??''));}if(t.status==='fulfilled')setTx(t.value);if(l.status==='fulfilled'){setBrokerage(l.value.operations);setLedgerAvailable(true)}else setLedgerAvailable(false);setNotice([p,c,t].some(x=>x.status==='rejected')?'Alguns dados não estão disponíveis nesta versão do backend.':'');}catch(e){setOnline(false);setNotice(`Backend indisponível: ${err(e)}`)}finally{setBusy(false)}}
 useEffect(()=>{void load()},[]);
 useEffect(()=>{
  let cancelled=false;
  const symbol=left.trim().toUpperCase();
  const optionType=optionTypeForStrategy(strategyA);
  if(!optionType||!/^[A-Z]{4}\d{1,2}$/.test(symbol)){setOptionRowsA([]);setOptionA('');return}
  const timer=window.setTimeout(()=>{void b3Api.currentOptions(symbol,optionType,150).then(r=>{if(cancelled)return;const rows=r.options.filter(x=>(x.quote.bid??0)>0);setOptionRowsA(rows);setOptionA(v=>rows.some(x=>x.contract.option_id===v)?v:'')}).catch(e=>{if(!cancelled){setOptionRowsA([]);setOptionA('');setNotice(`${optionType}s ${symbol}: ${err(e)}`)}})},300);
  return()=>{cancelled=true;window.clearTimeout(timer)}
 },[left,strategyA]);
 useEffect(()=>{
  let cancelled=false;
  const symbol=right.trim().toUpperCase();
  const optionType=optionTypeForStrategy(strategyB);
  if(!optionType||!/^[A-Z]{4}\d{1,2}$/.test(symbol)){setOptionRowsB([]);setOptionB('');return}
  const timer=window.setTimeout(()=>{void b3Api.currentOptions(symbol,optionType,150).then(r=>{if(cancelled)return;const rows=r.options.filter(x=>(x.quote.bid??0)>0);setOptionRowsB(rows);setOptionB(v=>rows.some(x=>x.contract.option_id===v)?v:'')}).catch(e=>{if(!cancelled){setOptionRowsB([]);setOptionB('');setNotice(`${optionType}s ${symbol}: ${err(e)}`)}})},300);
  return()=>{cancelled=true;window.clearTimeout(timer)}
 },[right,strategyB]);
 useEffect(()=>{
  const expiries=[...new Set(optionRowsA.filter(row=>row.contract.option_type==='PUT').map(row=>row.contract.expiration_date))].sort();
  setPutChainExpiry(value=>expiries.includes(value)?value:(expiries[0]||''));
  setPutCandidateIds(ids=>ids.filter(id=>optionRowsA.some(row=>row.contract.option_id===id)));
 },[optionRowsA]);
 async function run(
  task:string,
  conversation=false,
  options?:{ticker?:string|null;context?:Record<string,unknown>}
 ){
  if(!conversation){++inspectionSequence.current;setAnalysis(null);setNotice('')}
  const sequence=inspectionSequence.current;
  const current=()=>conversation||inspectionSequence.current===sequence;
  let deterministicResult:OrchestrateResponse|null=null;
  setBusy(true);
  const requestTicker = options && Object.prototype.hasOwnProperty.call(options,'ticker')
    ? options.ticker ?? null
    : ticker || null;
  const context: Record<string, unknown> = {
    workspace:page,
    research_mode:researchMode,
    selected_ticker:requestTicker,
    option_filter:filter||null,
    asset_view:assetView,
    horizon,
    ...(options?.context||{}),
  };
  // Workspace actions can use the deterministic dashboard fast path. Free-form
  // Copilot questions keep only contextual metadata so ambiguous/complex intent
  // can reach the senior reasoning path instead of being forced into a snapshot.
  const fastPathUseCases=dashboardFastPathUseCases[page];
  if(!conversation&&fastPathUseCases){context.dashboard_page=page;context.use_cases=fastPathUseCases}
  let pendingIndex=-1;
  if(conversation){
    setQuestion('');
    setChat(v=>{pendingIndex=v.length;return [...v,{q:task,r:null}]});
  }
  try{
    if(conversation && isOperationalStatusQuestion(task)){
      const health=await b3Api.health();
      const r:OrchestrateResponse={
        status:'ONLINE',
        result:{summary:`Sim. Estou conectado ao B3 Runtime em ${getApiBaseUrl()}.`,service:health.service,llm_enabled:health.llm_enabled},
        sources:[],
        audit:[],
        error:null,
      };
      setChat(v=>v.map((item,index)=>index===pendingIndex?{...item,r}:item));
      setOnline(true);
      return;
    }
    if(!conversation&&context.analysis_mode!=='deterministic'&&['Opportunities','Strategy Lab'].includes(page)){
      deterministicResult=await b3Api.orchestrate({task,ticker:requestTicker,context:{...context,analysis_mode:'deterministic',research_mode:'stored_only'}});
      if(!current())return;
      setAnalysis({...deterministicResult,result:{...deterministicResult.result,derived_synthesis_status:'PENDING'}});
    }
    const r=await b3Api.orchestrate({task,ticker:requestTicker,context});
    if(!current())return;
    if(conversation){
      setChat(v=>v.map((item,index)=>index===pendingIndex?{...item,r}:item));
    }else{
      const displayed=r.error&&deterministicResult?{...deterministicResult,error:r.error}:r;
      setAnalysis({...displayed,result:{...displayed.result,derived_synthesis_status:r.error?'FAILED':context.analysis_mode==='deterministic'?'NOT_REQUESTED':'COMPLETED'}});
    }
    setOnline(true);
  }catch(e){
    if(!current())return;
    const message=err(e);
    if(conversation){
      setChat(v=>v.map((item,index)=>index===pendingIndex?{...item,error:message}:item));
    }else{
      if(deterministicResult)setAnalysis({...deterministicResult,result:{...deterministicResult.result,derived_synthesis_status:'FAILED'}});
      setNotice(`Análise: ${message}`);
    }
  }finally{if(current())setBusy(false)}
 }
 function runOpportunityScreen(senior=false){
  const assets=opportunityAssets.split(/[,;\s]+/).filter(Boolean).map(value=>value.toUpperCase());
  void run(`UC-03: compare ${assets.join(', ')} pelo objetivo observado selecionado. Explique os dados favoráveis e contrários, lacunas e limites. Não transforme risco ou liquidez observados em previsão de retorno ou recomendação geral de compra.`,false,{ticker:null,context:{selected_ticker:null,opportunity_assets:assets,opportunity_objective:opportunityObjective,include_portfolio_stocks:includePortfolioStocks,...(senior?{}:{analysis_mode:'deterministic',research_mode:'stored_only'})}});
 }
 function openInStrategyLab(response:OrchestrateResponse|null=null){
  ++inspectionSequence.current;
  setPage('Strategy Lab');setBusy(false);setNotice('');
  const comparison=response?.result.strategy_comparison;
  if(comparison&&typeof comparison==='object'&&!Array.isArray(comparison)){
   setAnalysis(response);
  }else if(response?.result.put_chain_comparison){
   setAnalysis(response);
  }else{
   setLeft(ticker||asset);setAnalysis(null);
  }
 }
 async function importPortfolio(e:ChangeEvent<HTMLInputElement>){const f=e.target.files?.[0];e.target.value='';if(!f)return;setBusy(true);try{await b3Api.importPortfolio(f);await load();setNotice('Carteira validada e atualizada.')}catch(x){setNotice(`Importação recusada: ${err(x)}`)}finally{setBusy(false)}}
 async function importNotes(e:ChangeEvent<HTMLInputElement>){
  const files=[...(e.target.files||[])];e.target.value='';
  if(!files.length)return;
  if(files.length>100||files.some(f=>f.name.toLowerCase().endsWith('.zip'))&&files.length!==1){setNotice('Selecione até 100 PDFs ou um ZIP.');return}
  setBusy(true);
  try{
   if(files[0].name.toLowerCase().endsWith('.zip')){
    const result=await b3Api.importBrokerageBatch(files[0]);
    setBatch(JSON.stringify(result,null,2));
    setNotice(`Notas: ${result.files_processed} PDFs processados, ${result.files_failed} recusados, ${result.inserted_count} execuções inseridas. Confira o resultado por arquivo.`);
   }else{
    const results=[];
    for(const f of files){try{const r=await b3Api.importBrokerageNote(f);results.push({file:f.name,status:'processado',inseridas:r.inserted_count})}catch(x){results.push({file:f.name,status:'erro',detalhe:err(x)})}}
    setBatch(JSON.stringify(results,null,2));
    setNotice(`Notas: ${results.filter(r=>r.status==='processado').length} PDFs processados, ${results.filter(r=>r.status==='erro').length} recusados. Confira o resultado por arquivo.`);
   }
   await load();
  }catch(x){setNotice(`Lote: ${err(x)}`)}finally{setBusy(false)}
 }
 async function inspect(t:string){
  const v=t.trim().toUpperCase();
  if(!/^[A-Z0-9]{4,12}$/.test(v)){setNotice('Informe um ticker B3 válido.');return}
  const sequence=++inspectionSequence.current;
  const current=()=>inspectionSequence.current===sequence;
  setTicker(v);setAsset(v);setLive(null);setNews(null);setNewsError('');setFundamentals(null);setFundamentalsError('');setPilot(null);setAnalysis(null);setPersonalHistory(null);setNotice('');setBusy(true);
  // Publish independent evidence immediately. Stored research wins unless refresh was requested;
  // external news fills a real evidence gap without waiting for senior synthesis.
  const loadResearch=async()=>{
   let stored:ResearchNewsResponse|null=null;
   try{stored=await b3Api.storedResearch(v);if(current()&&researchMode!=='refresh'&&stored.events.length){setNews(stored);setNewsError('');return}}
   catch(error){if(researchMode==='stored_only'){if(current())setNewsError(`Research armazenado indisponível: ${err(error)}`);return}}
   if(researchMode==='stored_only')return;
   try{const fresh=await b3Api.researchNews(v);if(current()){setNews(fresh);setNewsError('')}}
   catch(error){if(current()){if(stored?.events.length)setNews(stored);setNewsError(`Busca externa indisponível: ${err(error)}`)}}
  };
  await Promise.allSettled([
    b3Api.personalHistory(v).then(value=>{if(current())setPersonalHistory(value)}),
    b3Api.fundamentals(v).then(value=>{if(current()){setFundamentals(value);setFundamentalsError('')}}).catch(error=>{if(current()){setFundamentals(null);setFundamentalsError(err(error))}}),
    b3Api.liveAnalysis(v).then(value=>{if(current())setLive(value)}).catch(error=>{if(current())setNotice(`Cotação/histórico indisponível: ${err(error)}`)}),
    loadResearch(),
    b3Api.pilotAnalysis(v).then(value=>{if(current())setPilot(value)}),
    b3Api.orchestrate({task:`UC-05/06/10: analise ${v} integrando preço atual, histórico, fundamentos, regime/fatores disponíveis, notícias/eventos e inteligência derivada B3/João. Preserve fatos canônicos, as_of, riscos, contradições, limitações e fontes.`,ticker:v,context:{workspace:'Market Intelligence',selected_ticker:v,asset_view:true,horizon,research_mode:researchMode}})
      .then(value=>{if(current()){setAnalysis(value);const context=value.result.research_context as {as_of?:string;tickers?:Record<string,{research_events?:ResearchNewsResponse['events']}>}|undefined;const events=context?.tickers?.[v]?.research_events;if(events)setNews({ticker:v,as_of:context?.as_of||'',events,source_refs:events.map(e=>e.source_ref).filter((ref):ref is string=>typeof ref==='string')})}})
      .catch(error=>{if(current())setNotice(`Inteligência integrada indisponível: ${err(error)}`)}),
  ]);
  if(current())setBusy(false);
 }

 const stocks=(portfolio?.positions||[]).filter(p=>p.instrument_type==='STOCK').sort((a,b)=>Math.abs(b.market_value||0)-Math.abs(a.market_value||0));const options=(portfolio?.positions||[]).filter(p=>p.instrument_type==='OPTION');
 const receivedIncomeCell=(symbol:string)=>{
  const income=portfolio?.received_income;
  if(!income)return 'Indisponível';
  const summary=income.summaries.find(row=>row.ticker===symbol);
  if(!summary)return 'Sem registro no período';
  return <span title={`Dividendos líquidos: ${brl(summary.dividends_net)}; JCP líquido: ${brl(summary.jcp_net)}; ${summary.payment_count} pagamentos; ${income.period_start} a ${income.period_end}`}>{brl(summary.total_net)}</span>;
 };
 const noteOpening=(p:PortfolioSnapshot['positions'][number])=>{const rows=brokerage.filter(o=>o.option_ticker===p.ticker);const side=p.quantity<0?'SELL':'BUY';if(!rows.length||rows.some(o=>o.side!==side||o.cash_flow==null)||Math.abs(rows.reduce((n,o)=>n+(o.side==='BUY'?o.quantity:-o.quantity),0)-p.quantity)>0.001)return null;return Math.abs(rows.reduce((n,o)=>n+(o.cash_flow||0),0))};
 const optionTable=(rows:PortfolioSnapshot['positions'])=><section className="panel"><h2>Opções abertas</h2><div className="table-wrap"><table><thead><tr>{['Ativo','Contrato','Tipo','Direção','Qtd.','Strike','Vencimento','Preço de aquisição','Preço atual','Valor BTG','Prêmio da nota','Resultado se encerrada agora'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{rows.map(p=><tr key={p.position_id} onClick={()=>setTicker(p.ticker)}><td>{p.underlying_ticker||'—'}</td><td>{p.ticker}</td><td>{p.option_type}</td><td>{p.quantity<0?'Vendida':'Comprada'}</td><td>{p.quantity}</td><td>{brl(p.strike)}</td><td>{p.expiration_date||'—'}</td><td title="Preço médio de entrada informado pelo backend">{brl(p.average_cost)}</td><td>{brl(p.market_price)}</td><td>{brl(p.market_value)}</td><td>{brl(noteOpening(p))}</td><td>{noteOpening(p)==null||p.market_value==null?'Sem conciliação':brl(p.quantity<0?noteOpening(p)!-Math.abs(p.market_value):Math.abs(p.market_value)-noteOpening(p)!)}</td></tr>)}</tbody></table></div>{!rows.length&&<p className="muted">Nenhuma opção aberta no snapshot BTG.</p>}</section>;
 const putExpiries=[...new Set(optionRowsA.filter(row=>row.contract.option_type==='PUT').map(row=>row.contract.expiration_date))].sort();
 const putRowsForExpiry=optionRowsA.filter(row=>row.contract.option_type==='PUT'&&row.contract.expiration_date===putChainExpiry);
 const allHistory=live?.market.price_history||[];
 const horizonDays:Record<string,number|undefined>={'1W':7,'1M':31,'3M':93,'6M':186,'1Y':366,'Tudo':undefined};
 const cutoffTime=live?new Date(live.as_of).getTime()-(horizonDays[horizon]??Infinity)*86400000:0;
 const visibleHistory=horizonDays[horizon]===undefined?allHistory:allHistory.filter(row=>new Date(row.observation_timestamp).getTime()>=cutoffTime);
 const coverageLimited=Boolean(live&&horizonDays[horizon]!==undefined&&allHistory.length&&new Date(allHistory[0].observation_timestamp).getTime()>cutoffTime);
 const quant=live?.market.quant||{};
 const quantValue=(key:string,digits=2,suffix='')=>{const value=quant[key];return typeof value==='number'&&Number.isFinite(value)?`${value.toFixed(digits)}${suffix}`:'Indisponível'};
 const quantPercent=(key:string)=>{const value=quant[key];return typeof value==='number'&&Number.isFinite(value)?`${(value*100).toFixed(2)}%`:'Indisponível'};
 const newsPanel=<section className="panel"><h2>Notícias e eventos verificados</h2>{newsError&&<div className="state-banner limited">{newsError}</div>}{news?.events.length?news.events.map((event,i)=>{const headline=eventText(event,'headline','title','event_type')||`Evento ${i+1}`;const summary=eventText(event,'summary','description');const date=eventText(event,'published_at','published_date','available_timestamp');const source=eventText(event,'source_name','source');const url=eventUrl(event);return <article className="research-event" key={String(event.source_record_id||url||i)}><h3>{url?<a href={url} target="_blank" rel="noreferrer">{headline}</a>:headline}</h3>{date&&<small>{when(date)}{source?` · ${source}`:''}</small>}{summary&&<p>{summary}</p>}</article>}):<p className="muted">{busy?'Carregando research existente; busca externa será usada se faltar evidência.':'Nenhuma notícia datada e verificável disponível.'}</p>}{news?.excluded_future_count? <p className="muted">{news.excluded_future_count} registro(s) com publicação futura foram excluídos no corte {when(news.as_of)}.</p>:null}{news?.source_refs?.length?<small className="muted">Fontes: {news.source_refs.join(' · ')} · as_of {when(news.as_of)}</small>:null}</section>;
 return <div className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Carteira · Opções · Inteligência</small></div></div><button className="backend-button" onClick={()=>setSettings(true)}><span className={online?'online-dot':'offline-dot'}>●</span> {online?'Conectado':'Offline'} · {getApiBaseUrl()}</button></header><div className="body"><aside className="sidebar"><nav>{pages.map((p,i)=><button key={p} className={`nav-item ${page===p?'active':''}`} onClick={()=>{++inspectionSequence.current;setPage(p);setAnalysis(null);setBusy(false)}}><span className="nav-icon">{['◫','◈','◎','⇄','◌'][i]}</span><strong>{p}</strong></button>)}</nav><section className="connections"><h3>Dados</h3><label className="load">{portfolio?.updated_at?'Atualizar carteira BTG':'Carregar carteira BTG'}<input hidden type="file" accept=".xlsx,.xlsm" onChange={importPortfolio}/></label><label className="load secondary">Carregar notas PDF / ZIP<input hidden type="file" accept=".pdf,.zip" multiple onChange={importNotes}/></label><button className="load secondary" onClick={()=>setCapitalEdit(true)}>Capital disponível</button><button className="load secondary" onClick={()=>setSettings(true)}>Configurar servidor Ubuntu</button><small>Carteira: {when(portfolio?.updated_at)}</small>{batch&&<details><summary>Resultado das notas</summary><pre>{batch}</pre></details>}</section></aside><main className="workspace"><div className="workspace-head"><div><h1>{page}</h1><p>{page==='Portfolio'?`Snapshot BTG: ${portfolio?.as_of||'Indisponível'}`:'Fatos canônicos · decisão humana'}</p></div><button className="refresh" disabled={busy} onClick={()=>{void load();if(page!=='Portfolio')void run(`Atualize ${page} com fatos, datas e fontes.`)}}>{busy?'Carregando…':'Atualizar'}</button></div>{notice&&<div className="state-banner limited" role="status">{notice}</div>}{['Opportunities','Market Intelligence','Strategy Lab'].includes(page)&&<label className="research-policy">Notícias e eventos <select value={researchMode} onChange={e=>setResearchMode(e.target.value)}><option value="stored_first">Reusar base e buscar lacunas</option><option value="stored_only">Somente research armazenado</option><option value="refresh">Atualizar research externo</option></select><small>Aplica-se ao research; cotações e fundamentos seguem seus provedores.</small></label>}
 {page==='Portfolio'&&<><div className="cards"><div className="metric"><span>Capital utilizável</span><strong>{brl(capital?.usable_capital)}</strong><small>Reserva: {brl(capital?.minimum_reserve)}</small></div><div className="metric"><span>Valor das ações</span><strong>{stocks.length?brl(stocks.reduce((a,p)=>a+(p.market_value||0),0)):'Indisponível'}</strong><small>Snapshot: {portfolio?.as_of||'—'}</small></div><div className="metric"><span>Opções abertas</span><strong>{options.length}</strong><small>Snapshot BTG</small></div></div><section className="panel"><h2>Ações · valor atual decrescente</h2>{portfolio?.received_income&&<p className="muted">Dividendos/JCP líquidos recebidos no extrato: {portfolio.received_income.period_start} a {portfolio.received_income.period_end}.</p>}<div className="table-wrap"><table><thead><tr>{['Ativo','Qtd.','Custo médio','Último preço','Valor atual','Resultado econômico','Dividendos/JCP líquidos recebidos','Proventos anunciados'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{stocks.map(p=><tr key={p.position_id} onClick={()=>setTicker(p.ticker)}><td>{p.ticker}{p.quantity<0?' · SHORT':''}</td><td>{p.quantity}</td><td>{brl(p.average_cost)}</td><td>{brl(p.market_price)}</td><td>{brl(p.market_value)}</td><td>Indisponível</td><td>{receivedIncomeCell(p.ticker)}</td><td>Indisponível</td></tr>)}</tbody></table></div>{!stocks.length&&<p className="muted">Importe o Excel BTG para ver as posições.</p>}</section><section className="panel"><h2>Aquisição × valor atual</h2><p className="muted">Base de aquisição indisponível no contrato atual. O gráfico será exibido quando o backend fornecer esse valor canônico.</p></section>{optionTable(options)}</>}
 {page==='Options'&&<OptionsWorkspace positions={options} operations={brokerage} ledgerAvailable={ledgerAvailable} onSelect={setTicker}/>}
 {page==='Opportunities'&&<><div className="toolbar"><form onSubmit={e=>{e.preventDefault();const requested=asset.toUpperCase();setTicker(requested);void run(`UC-03: analise ${requested} sob demanda, elegibilidade, risco, evidências e ranking canônico disponível.`,false,{ticker:requested,context:{selected_ticker:requested}})}}><label>Analisar ativo <input required value={asset} onChange={e=>setAsset(e.target.value)} placeholder="PETR4"/></label><button>Analisar</button></form><form onSubmit={e=>{e.preventDefault();runOpportunityScreen()}}>
 <label>Universo de ações (até 20)<input required value={opportunityAssets} onChange={e=>setOpportunityAssets(e.target.value)} placeholder="VALE3, RENT3, VIVT3, BBAS3"/></label>
 <label>Objetivo da comparação<select value={opportunityObjective} onChange={e=>setOpportunityObjective(e.target.value)}><option value="COMPARE_ONLY">Comparar sem ranking</option><option value="LOWEST_REALIZED_VOLATILITY_60D">Menor volatilidade realizada · 60 retornos</option><option value="HIGHEST_OBSERVED_LIQUIDITY_20D">Maior proxy de liquidez · 20 observações</option></select></label>
 <label><input type="checkbox" checked={includePortfolioStocks} onChange={e=>setIncludePortfolioStocks(e.target.checked)}/> Incluir ações da carteira (união até 20)</label>
 <button disabled={busy}>Comparar / ordenar</button> <button type="button" disabled={busy} onClick={()=>runOpportunityScreen(true)}>Analisar comparação</button>
 </form></div><section className="panel"><h2>Ranking · risco × oportunidade</h2><p className="muted">Scores e classificação são mostrados somente quando fornecidos pelo pipeline canônico.</p><AnalysisOutput data={analysis}/><button disabled={busy} onClick={()=>openInStrategyLab(analysis)}>Comparar no Strategy Lab</button></section></>}
 {page==='Strategy Lab'&&<><section className="panel"><h2>Troca financiada de ações</h2><form className="lab-form" onSubmit={e=>{e.preventDefault();void run(`Compare manter ${fundedQuantity} ações ${left} versus vender essa quantidade para financiar ${right}. Explique o fluxo de caixa e restrições; não invente custos, retorno ou execução.`,false,{ticker:null,context:{selected_ticker:null,comparison_assets:[left.trim().toUpperCase(),right.trim().toUpperCase()],funded_switch:{quantity:Number(fundedQuantity),fees_brl:fundedFees===''?null:Number(fundedFees),taxes_brl:fundedTaxes===''?null:Number(fundedTaxes)}}})}}><label>Ação a vender<input required value={left} onChange={e=>setLeft(e.target.value)}/></label><label>Ação a comprar<input required value={right} onChange={e=>setRight(e.target.value)}/></label><label>Quantidade a vender<input required type="number" min="1" step="1" value={fundedQuantity} onChange={e=>setFundedQuantity(e.target.value)}/></label><label>Custos totais do cenário (R$)<input type="number" min="0" step="0.01" value={fundedFees} onChange={e=>setFundedFees(e.target.value)} placeholder="UNKNOWN se vazio"/></label><label>Impostos informados do cenário (R$)<input type="number" min="0" step="0.01" value={fundedTaxes} onChange={e=>setFundedTaxes(e.target.value)} placeholder="UNKNOWN se vazio"/></label><button disabled={busy}>Comparar troca financiada</button><p className="muted">Custos e impostos são premissas informadas; não são estimados automaticamente. A comparação não executa ordens.</p></form><h2>Comparar alternativas</h2><form className="lab-form" onSubmit={e=>{e.preventDefault();const assetA=left.toUpperCase();const assetB=right.toUpperCase();const optionTextA=optionTypeForStrategy(strategyA)&&optionA?` contrato ${optionA}`:'';const optionTextB=optionTypeForStrategy(strategyB)&&optionB?` contrato ${optionB}`:'';const shocks=scenarioShocks.trim()?scenarioShocks.split(',').map(value=>Number(value.trim())):[];void run(`UC-04: compare ${strategyA} em ${assetA}${optionTextA} e ${strategyB} em ${assetB}${optionTextB}${amount?`, valor informado R$ ${amount}`:''}. Use cotações atuais OPLAB separadas do histórico. Mostre cenários, premissas e riscos canônicos; não atribua probabilidade aos choques.`,false,{ticker:null,context:{selected_ticker:null,comparison_assets:[assetA,assetB],strategy_a:strategyA,strategy_b:strategyB,option_a:optionTypeForStrategy(strategyA)?optionA:null,option_b:optionTypeForStrategy(strategyB)?optionB:null,comparison_amount:amount?Number(amount):null,scenario_horizon:scenarioHorizon||null,scenario_shocks_pct:scenarioHorizon?shocks:null,scenario_objective:scenarioObjective,put_objective:strategyA==='Vender PUT'&&strategyB==='Vender PUT'?putPairObjective:'COMPARE_ONLY'}})}}>{strategyA==='Vender PUT'&&strategyB==='Vender PUT'&&<label>Objetivo das duas PUTs<select value={putPairObjective} onChange={e=>setPutPairObjective(e.target.value)}><option value="COMPARE_ONLY">Comparar sem vencedor</option><option value="LOWEST_MODEL_EXPIRY_ITM">Menor estimativa de ITM no próprio vencimento</option><option value="HIGHEST_GROSS_PREMIUM_PER_CAPITAL_30D">Maior prêmio bruto por capital normalizado a 30 dias</option></select><small>Vencimentos podem diferir. Prêmio bruto não é retorno esperado; ITM não é probabilidade comprovada de exercício.</small></label>}<label>Ativo A<input required value={left} onChange={e=>setLeft(e.target.value)} placeholder="ITUB4"/></label><label>Estratégia A<select value={strategyA} onChange={e=>setStrategyA(e.target.value)}>{['Comprar ação','Vender/reduzir ação','Vender PUT','Vender CALL coberta','Manter'].map(x=><option key={x}>{x}</option>)}</select></label>{optionTypeForStrategy(strategyA)&&<label>{optionTypeForStrategy(strategyA)} A<select required value={optionA} onChange={e=>setOptionA(e.target.value)}><option value="">Selecione contrato OPLAB</option>{optionRowsA.map(row=><option key={row.contract.option_id} value={row.contract.option_id}>{row.contract.option_id} · Strike {brl(row.contract.strike)} · {row.contract.expiration_date} · Bid {brl(row.quote.bid)} · Ask {brl(row.quote.ask)} · Last {brl(row.quote.last)}</option>)}</select></label>}<label>Ativo B<input required value={right} onChange={e=>setRight(e.target.value)} placeholder="WEGE3"/></label><label>Estratégia B<select value={strategyB} onChange={e=>setStrategyB(e.target.value)}>{['Vender PUT','Vender CALL coberta','Vender/reduzir ação','Comprar ação','Manter'].map(x=><option key={x}>{x}</option>)}</select></label>{optionTypeForStrategy(strategyB)&&<label>{optionTypeForStrategy(strategyB)} B<select required value={optionB} onChange={e=>setOptionB(e.target.value)}><option value="">Selecione contrato OPLAB</option>{optionRowsB.map(row=><option key={row.contract.option_id} value={row.contract.option_id}>{row.contract.option_id} · Strike {brl(row.contract.strike)} · {row.contract.expiration_date} · Bid {brl(row.quote.bid)} · Ask {brl(row.quote.ask)} · Last {brl(row.quote.last)}</option>)}</select></label>}<label>Valor a simular em R$ {strategyA==='Vender/reduzir ação'||strategyB==='Vender/reduzir ação'?'(obrigatório para redução)':'(opcional)'}<input type="number" min="0" required={strategyA==='Vender/reduzir ação'||strategyB==='Vender/reduzir ação'} value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Horizonte comum dos cenários<input type="date" value={scenarioHorizon} onChange={e=>setScenarioHorizon(e.target.value)}/></label><label>Choques de preço em % (separados por vírgula)<input value={scenarioShocks} onChange={e=>setScenarioShocks(e.target.value)} placeholder="-10, 0, 10"/></label><label>Objetivo<select value={scenarioObjective} onChange={e=>setScenarioObjective(e.target.value)}><option value="COMPARE_ONLY">Comparar sem ranking</option><option value="MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL">Maior retorno no pior cenário informado</option></select></label><button>Comparar</button><p className="muted">Sem horizonte, a comparação fundamental continua disponível sem payoff projetado. Para opções, o horizonte precisa coincidir com o vencimento. Choques são hipóteses suas, não previsões ou probabilidades. PUT usa 1 contrato cash-secured e o bid atual; CALL exige cobertura na carteira. Reduzir ação usa valor nocional e não infere quantidade executável, impostos, taxas ou slippage.</p></form></section>{page==='Strategy Lab'&&<section className="panel"><h2>Comparar strikes PUT</h2><p className="muted">Use Ativo A com estratégia “Vender PUT” para carregar uma única cadeia OPLAB; selecione contratos do mesmo vencimento. Bid, spread, liquidez e cenários são comparados sem substituir contratos.</p><form className="lab-form" onSubmit={e=>{e.preventDefault();const shocks=scenarioShocks.trim()?scenarioShocks.split(',').map(value=>Number(value.trim())):[];void run(`UC-04: compare ${putCandidateIds.length} PUT strikes de ${left.toUpperCase()} para ${putChainExpiry}.`,false,{ticker:null,context:{selected_ticker:null,comparison_ticker:left.toUpperCase(),put_candidate_option_ids:putCandidateIds,scenario_horizon:putChainExpiry||null,scenario_shocks_pct:putChainExpiry?shocks:null,scenario_objective:scenarioObjective}})}}><label>Ativo<input required value={left} onChange={e=>setLeft(e.target.value)} placeholder="VALE3"/></label><label>Vencimento<select required value={putChainExpiry} onChange={e=>{setPutChainExpiry(e.target.value);setPutCandidateIds([])}}><option value="">Selecione vencimento</option>{putExpiries.map(expiry=><option key={expiry} value={expiry}>{expiry}</option>)}</select></label>{putRowsForExpiry.map(row=><label key={row.contract.option_id} className="candidate-option"><input type="checkbox" checked={putCandidateIds.includes(row.contract.option_id)} onChange={e=>setPutCandidateIds(ids=>e.target.checked?[...ids,row.contract.option_id]:ids.filter(id=>id!==row.contract.option_id))}/>{row.contract.option_id} · Strike {brl(row.contract.strike)} · Bid {brl(row.quote.bid)} · Ask {brl(row.quote.ask)} · IV {row.quote.implied_volatility??'UNKNOWN'} · Volume {row.quote.volume??'UNKNOWN'} · OI {row.quote.open_interest??'UNKNOWN'}</label>)}<button disabled={putCandidateIds.length<2||busy}>Comparar {putCandidateIds.length} PUTs</button><p className="muted">Cenários e objetivo usam os controles gerais abaixo. Estimativas de ITM/touch dependem de IV e são não calibradas; assignment antecipado e frequência pessoal permanecem campos separados.</p></form></section>}<section className="panel"><h2>Comparação</h2><p className="muted">P&amp;L por cenário, quando solicitado, não escolhe um vencedor nem substitui sua tolerância a risco.</p><AnalysisOutput data={analysis}/></section></>}
 {page==='Market Intelligence'&&<><div className="workspace-tabs"><button className={!assetView?'selected':''} onClick={()=>setAssetView(false)}>Contexto de mercado</button><button className={assetView?'selected':''} onClick={()=>setAssetView(true)}>Ativo · gráfico e indicadores</button></div>{!assetView?<section className="panel"><h2>Regime, fatores e eventos</h2><p className="muted">Esta aba resume o mercado amplo. Para cotação, gráfico histórico, volume e indicadores de um ticker, abra a análise de ativo.</p><button onClick={()=>void run('UC-05/06/10: regime, drivers, taxas, câmbio, fluxo, fatores e eventos com data, qualidade e fontes; associação não é causalidade.')}>Analisar contexto</button> <button onClick={()=>{const selected=asset.trim()||ticker.trim();setAssetView(true);if(selected)void inspect(selected)}}>Analisar ativo · abrir gráfico</button><AnalysisOutput data={analysis}/></section>:<><div className="toolbar"><form onSubmit={e=>{e.preventDefault();void inspect(asset)}}><label>Ativo B3 <input required value={asset} onChange={e=>setAsset(e.target.value)} placeholder="PETR4"/></label><button>Analisar</button></form><div>{['1W','1M','3M','6M','1Y','Tudo'].map(h=><button key={h} className={h===horizon?'selected':''} onClick={()=>setHorizon(h)}>{h}</button>)}</div></div><div className="cards"><div className="metric"><span>Ativo</span><strong>{ticker||'—'}</strong><small>{when(live?.as_of)}</small></div><div className="metric"><span>Último preço</span><strong>{brl(live?.market.latest.close)}</strong><small>{when(live?.market.latest.observation_timestamp)} · {live?.market.latest.source||'Fonte indisponível'}</small></div><div className="metric"><span>Volume</span><strong>{live?.market.latest.volume??'—'}</strong><small>Registro de {when(live?.market.latest.observation_timestamp)}</small></div></div>{newsPanel}<section className="panel"><h2>Histórico de preços · {horizon}</h2>{live?<><p className="muted">Fechamento ajustado quando disponível; caso contrário, fechamento. {visibleHistory.length} de {live.market.history_count} registros · {allHistory.length?when(allHistory[0].observation_timestamp):'sem data inicial'} a {allHistory.length?when(allHistory[allHistory.length-1].observation_timestamp):'—'} · dados até {when(live.as_of)} · {live.source_refs.join(' · ')}</p>{coverageLimited&&<div className="state-banner limited">A janela {horizon} foi solicitada, mas o histórico começa em {when(allHistory[0].observation_timestamp)}; o gráfico cobre somente os registros disponíveis.</div>}<HistoryChart records={visibleHistory}/></>:<p className="muted">Aguardando histórico do backend.</p>}</section><section className="panel"><h2>Indicadores técnicos · amostra point-in-time disponível</h2>{live?<><p className="muted">Cálculo determinístico no backend sobre {live.market.history_count} registros disponíveis em {when(live.as_of)}. Valores sem amostra suficiente permanecem indisponíveis.</p><div className="indicator-grid"><div><span>RSI (14)</span><strong>{quantValue('rsi_14')}</strong></div><div><span>SMA (20)</span><strong>{typeof quant.sma_20==='number'?brl(quant.sma_20):'Indisponível'}</strong></div><div><span>SMA (50)</span><strong>{typeof quant.sma_50==='number'?brl(quant.sma_50):'Indisponível'}</strong></div><div><span>SMA (200)</span><strong>{typeof quant.sma_200==='number'?brl(quant.sma_200):'Indisponível'}</strong></div><div><span>Volatilidade anualizada (20d)</span><strong>{quantPercent('volatility_20d')}</strong></div><div><span>Volatilidade anualizada (60d)</span><strong>{quantPercent('volatility_60d')}</strong></div><div><span>MACD</span><strong>{typeof quant.macd==='number'?brl(quant.macd):'Indisponível'}</strong></div><div><span>Drawdown máximo na amostra</span><strong>{quantPercent('max_drawdown')}</strong></div></div></>:<p className="muted">Aguardando histórico e cálculos do backend.</p>}</section><section className="panel"><h2>Inteligência integrada · B3 + João + mercado</h2>{busy&&!analysis&&<p className="muted" role="status">Síntese em andamento. Evidências disponíveis aparecem assim que chegam.</p>}{!analysis&&<PersonalHistory value={personalHistory}/>}<AnalysisOutput data={analysis}/></section><section className="panel"><h2>Fundamentos e alvos institucionais</h2>{fundamentalsError&&<div className="state-banner limited">Fundamentos indisponíveis: {fundamentalsError}</div>}{fundamentals?.metrics.length?<><p className="muted">BRAPI · consulta em {when(fundamentals.as_of)}. Observação/report date por métrica; disponibilidade histórica não é presumida.</p><div className="table-wrap"><table><thead><tr><th>Métrica</th><th>Valor</th><th>Período</th><th>Data observada</th><th>Qualidade</th></tr></thead><tbody>{fundamentals.metrics.map((metric,index)=><tr key={metric.source_record_id||String(index)}><td>{metric.metric}</td><td>{fundamentalValue(metric)}</td><td>{metric.period_type||'Indisponível'}</td><td>{metric.report_date||when(metric.observation_timestamp)}</td><td>{metric.quality_status}{metric.quality_flags.length?' · '+metric.quality_flags.join(', '):''}</td></tr>)}</tbody></table></div></>:<p className="muted">{fundamentalsError?'A consulta à fonte fundamental falhou.':fundamentals?.status==='NO_DATA'?'BRAPI não retornou métricas admissíveis para este ticker.':busy?'Consultando fundamentos…':'Fundamentos indisponíveis.'}</p>}{fundamentals?.excluded_future_count? <p className="muted">{fundamentals.excluded_future_count} registros futuros foram excluídos do corte.</p>:null}<p className="muted">Preço-alvo de analistas: UNKNOWN · não há fonte verificada configurada para instituições, data e referência. Não estimado pelo agente.</p>{fundamentals?.limitations.map(item=><p className="muted" key={item}>{item}</p>)}</section><section className="panel"><h2>Piloto de inteligência · DeepSeek + OpenClaw</h2>{pilot?.status==='NOT_AVAILABLE'?<p className="muted">Ainda não há análise do lote de 20 ações para este ativo.</p>:pilot?.evidence?<><p className="muted">Evidências coletadas em {when(pilot.evidence.collected_at)}{pilot.evidence.latest_market_record?` · Cotação de ${when(pilot.evidence.latest_market_record.observation_timestamp)}`: ''} · {pilot.evidence.source_refs.length} referências</p><div className="llm-columns"><div><h3>DeepSeek local · {pilot.deepseek_status||'pendente'}</h3><p>{pilot.deepseek?.analysis||pilot.deepseek_error||'Aguardando execução.'}</p></div><div><h3>OpenClaw / ChatGPT · {pilot.openclaw_status||'pendente'}</h3><p>{pilot.openclaw?.analysis.summary||pilot.openclaw_error||'Aguardando execução.'}</p>{pilot.openclaw?.analysis.risks?.length?<details><summary>Riscos</summary><ul>{pilot.openclaw.analysis.risks.map((r,i)=><li key={i}>{r}</li>)}</ul></details>:null}{pilot.openclaw?.analysis.limitations?.length?<details><summary>Limitações</summary><ul>{pilot.openclaw.analysis.limitations.map((r,i)=><li key={i}>{r}</li>)}</ul></details>:null}</div></div><details><summary>Fontes usadas ({pilot.evidence.source_refs.length})</summary>{pilot.evidence.source_refs.map((ref,i)=><p key={i}>{ref}</p>)}</details></>:<p className="muted">Selecione um ativo para consultar o piloto.</p>}</section></>}</>}
 </main><aside className="copilot"><div className="copilot-head"><strong>Copilot</strong><span className={online?'online-dot':'offline-dot'}>●</span></div><p className="context">Contexto: {ticker?`${ticker} / `:''}{page}{assetView&&page==='Market Intelligence'?' / Ativo':''}</p><button disabled={busy} onClick={()=>void run(`Faça um panorama de ${page}${ticker?` para ${ticker}`:''}; fatos, riscos, contradições, limitações e fontes.`,true)}>Visão geral</button><div className="conversation">{chat.map((c,i)=><div className="answer-card" key={i}><b>Você: {c.q}</b>{c.error?<div className="state-banner error"><strong>Erro no runtime</strong><span>{c.error}</span></div>:c.r?<><AnalysisOutput data={c.r}/>{(c.r.result.strategy_comparison||c.r.result.put_chain_comparison)?<button disabled={busy} onClick={()=>openInStrategyLab(c.r)}>Abrir comparação no Strategy Lab</button>:null}</>:<p className="muted" role="status">Analisando no runtime B3…</p>}</div>)}</div><form className="chat-form" onSubmit={e=>{e.preventDefault();if(question.trim())void run(question.trim(),true)}}><textarea value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Pergunte sobre a seleção atual…" rows={4}/><button disabled={busy||!question.trim()}>Enviar</button></form></aside></div>
 {settings&&<div className="modal-backdrop" onClick={()=>setSettings(false)}><div className="transaction-modal" onClick={e=>e.stopPropagation()}><h2>Servidor Ubuntu · API B3</h2><form className="transaction-form" onSubmit={async(e:FormEvent)=>{e.preventDefault();try{setApiBaseUrl(url);setSettings(false);setPortfolio(null);setCapital(null);await load()}catch(x){setNotice(err(x))}}}><label>IP ou hostname e porta</label><input value={url} onChange={e=>setUrl(e.target.value)} placeholder="http://ubuntu:8000"/><small>{url}</small><button>Salvar e testar conexão</button></form><button onClick={()=>setSettings(false)}>Fechar</button></div></div>}
 {capitalEdit&&<div className="modal-backdrop" onClick={()=>setCapitalEdit(false)}><div className="transaction-modal" onClick={e=>e.stopPropagation()}><h2>Capital BTG</h2><form className="transaction-form" onSubmit={async(e:FormEvent)=>{e.preventDefault();try{const c=await b3Api.saveCapital(Number(available),Number(reserve));setCapital(c);setCapitalEdit(false);setNotice('Capital salvo no backend.')}catch(x){setNotice(err(x))}}}><label>Capital disponível (R$)</label><input type="number" min="0" step="0.01" required value={available} onChange={e=>setAvailable(e.target.value)}/><label>Reserva mínima (R$)</label><input type="number" min="0" step="0.01" required value={reserve} onChange={e=>setReserve(e.target.value)}/><button>Salvar no backend</button></form><button onClick={()=>setCapitalEdit(false)}>Fechar</button></div></div>}
 </div>;
}
