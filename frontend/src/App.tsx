import { ChangeEvent, FormEvent, useEffect, useRef, useState } from 'react';
import { b3Api, getApiBaseUrl, setApiBaseUrl } from './api/client';
import OptionsWorkspace from './OptionsWorkspace';
import AnalysisOutput from './components/AnalysisOutput';
import PersonalHistory from './components/PersonalHistory';
import type { CapitalProfile, PortfolioSnapshot, BrokerageOperation, PilotAnalysis, OrchestrateResponse, TransactionResponse, LiveAnalysisResponse, ResearchNewsResponse, CurrentOptionRow } from './api/contracts';

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
function isOperationalStatusQuestion(task:string){
 const normalized=task.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9 ]/g,' ').replace(/\s+/g,' ').trim();
 return /^(vc |voce |copilot |sistema )?(esta|ta) (on|online|conectado|funcionando)$/.test(normalized)
   || /^(status|status do sistema|esta conectado|esta funcionando)$/.test(normalized);
}
export default function App(){
 const inspectionSequence=useRef(0);
 const [researchMode,setResearchMode]=useState("stored_first");
 const [personalHistory,setPersonalHistory]=useState<Record<string,unknown>|null>(null);
 const [page,setPage]=useState<Page>('Portfolio'),[online,setOnline]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const [portfolio,setPortfolio]=useState<PortfolioSnapshot|null>(null),[capital,setCapital]=useState<CapitalProfile|null>(null),[tx,setTx]=useState<TransactionResponse[]>([]);
 const [brokerage,setBrokerage]=useState<BrokerageOperation[]>([]),[ledgerAvailable,setLedgerAvailable]=useState(false);
 const [url,setUrl]=useState(getApiBaseUrl()),[settings,setSettings]=useState(false),[capitalEdit,setCapitalEdit]=useState(false),[available,setAvailable]=useState(''),[reserve,setReserve]=useState('');
 const [ticker,setTicker]=useState(''),[asset,setAsset]=useState(''),[filter,setFilter]=useState(''),[analysis,setAnalysis]=useState<OrchestrateResponse|null>(null);
 const [live,setLive]=useState<LiveAnalysisResponse|null>(null),[news,setNews]=useState<ResearchNewsResponse|null>(null),[pilot,setPilot]=useState<PilotAnalysis|null>(null),[horizon,setHorizon]=useState('1M'),[assetView,setAssetView]=useState(false);
 const [question,setQuestion]=useState(''),[chat,setChat]=useState<{q:string;r:OrchestrateResponse|null;error?:string}[]>([]),[batch,setBatch]=useState<string>('');
 const [left,setLeft]=useState(''),[right,setRight]=useState(''),[strategyA,setStrategyA]=useState('Comprar ação'),[strategyB,setStrategyB]=useState('Vender PUT'),[amount,setAmount]=useState('');
 const [scenarioHorizon,setScenarioHorizon]=useState(''),[scenarioShocks,setScenarioShocks]=useState('-10, 0, 10');
 const [optionA,setOptionA]=useState(''),[optionB,setOptionB]=useState(''),[optionRowsA,setOptionRowsA]=useState<CurrentOptionRow[]>([]),[optionRowsB,setOptionRowsB]=useState<CurrentOptionRow[]>([]);
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
 async function run(
  task:string,
  conversation=false,
  options?:{ticker?:string|null;context?:Record<string,unknown>}
 ){
  if(!conversation)++inspectionSequence.current;
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
    const r=await b3Api.orchestrate({task,ticker:requestTicker,context});
    if(conversation){
      setChat(v=>v.map((item,index)=>index===pendingIndex?{...item,r}:item));
    }else setAnalysis(r);
    setOnline(true);
  }catch(e){
    const message=err(e);
    if(conversation){
      setChat(v=>v.map((item,index)=>index===pendingIndex?{...item,error:message}:item));
    }else{
      setNotice(`Análise: ${message}`);
    }
  }finally{setBusy(false)}
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
  setTicker(v);setAsset(v);setLive(null);setNews(null);setPilot(null);setAnalysis(null);setPersonalHistory(null);setNotice('');setBusy(true);
  // Publish independently completed evidence; one slow model never holds these cards.
  await Promise.allSettled([
    b3Api.personalHistory(v).then(value=>{if(current())setPersonalHistory(value)}),
    b3Api.liveAnalysis(v).then(value=>{if(current())setLive(value)}).catch(error=>{if(current())setNotice(`Cotação indisponível: ${err(error)}`)}),
    b3Api.storedResearch(v).then(value=>{if(current())setNews(value)}),
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
 return <div className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Carteira · Opções · Inteligência</small></div></div><button className="backend-button" onClick={()=>setSettings(true)}><span className={online?'online-dot':'offline-dot'}>●</span> {online?'Conectado':'Offline'} · {getApiBaseUrl()}</button></header><div className="body"><aside className="sidebar"><nav>{pages.map((p,i)=><button key={p} className={`nav-item ${page===p?'active':''}`} onClick={()=>{++inspectionSequence.current;setPage(p);setAnalysis(null);setBusy(false)}}><span className="nav-icon">{['◫','◈','◎','⇄','◌'][i]}</span><strong>{p}</strong></button>)}</nav><section className="connections"><h3>Dados</h3><label className="load">{portfolio?.updated_at?'Atualizar carteira BTG':'Carregar carteira BTG'}<input hidden type="file" accept=".xlsx,.xlsm" onChange={importPortfolio}/></label><label className="load secondary">Carregar notas PDF / ZIP<input hidden type="file" accept=".pdf,.zip" multiple onChange={importNotes}/></label><button className="load secondary" onClick={()=>setCapitalEdit(true)}>Capital disponível</button><button className="load secondary" onClick={()=>setSettings(true)}>Configurar servidor Ubuntu</button><small>Carteira: {when(portfolio?.updated_at)}</small>{batch&&<details><summary>Resultado das notas</summary><pre>{batch}</pre></details>}</section></aside><main className="workspace"><div className="workspace-head"><div><h1>{page}</h1><p>{page==='Portfolio'?`Snapshot BTG: ${portfolio?.as_of||'Indisponível'}`:'Fatos canônicos · decisão humana'}</p></div><button className="refresh" disabled={busy} onClick={()=>{void load();if(page!=='Portfolio')void run(`Atualize ${page} com fatos, datas e fontes.`)}}>{busy?'Carregando…':'Atualizar'}</button></div>{notice&&<div className="state-banner limited" role="status">{notice}</div>}{['Opportunities','Market Intelligence','Strategy Lab'].includes(page)&&<label className="research-policy">Notícias e eventos <select value={researchMode} onChange={e=>setResearchMode(e.target.value)}><option value="stored_first">Reusar base e buscar lacunas</option><option value="stored_only">Somente research armazenado</option><option value="refresh">Atualizar research externo</option></select><small>Aplica-se ao research; cotações e fundamentos seguem seus provedores.</small></label>}
 {page==='Portfolio'&&<><div className="cards"><div className="metric"><span>Capital utilizável</span><strong>{brl(capital?.usable_capital)}</strong><small>Reserva: {brl(capital?.minimum_reserve)}</small></div><div className="metric"><span>Valor das ações</span><strong>{stocks.length?brl(stocks.reduce((a,p)=>a+(p.market_value||0),0)):'Indisponível'}</strong><small>Snapshot: {portfolio?.as_of||'—'}</small></div><div className="metric"><span>Opções abertas</span><strong>{options.length}</strong><small>Snapshot BTG</small></div></div><section className="panel"><h2>Ações · valor atual decrescente</h2>{portfolio?.received_income&&<p className="muted">Dividendos/JCP líquidos recebidos no extrato: {portfolio.received_income.period_start} a {portfolio.received_income.period_end}.</p>}<div className="table-wrap"><table><thead><tr>{['Ativo','Qtd.','Custo médio','Último preço','Valor atual','Resultado econômico','Dividendos/JCP líquidos recebidos','Proventos anunciados'].map(x=><th key={x}>{x}</th>)}</tr></thead><tbody>{stocks.map(p=><tr key={p.position_id} onClick={()=>setTicker(p.ticker)}><td>{p.ticker}{p.quantity<0?' · SHORT':''}</td><td>{p.quantity}</td><td>{brl(p.average_cost)}</td><td>{brl(p.market_price)}</td><td>{brl(p.market_value)}</td><td>Indisponível</td><td>{receivedIncomeCell(p.ticker)}</td><td>Indisponível</td></tr>)}</tbody></table></div>{!stocks.length&&<p className="muted">Importe o Excel BTG para ver as posições.</p>}</section><section className="panel"><h2>Aquisição × valor atual</h2><p className="muted">Base de aquisição indisponível no contrato atual. O gráfico será exibido quando o backend fornecer esse valor canônico.</p></section>{optionTable(options)}</>}
 {page==='Options'&&<OptionsWorkspace positions={options} operations={brokerage} ledgerAvailable={ledgerAvailable} onSelect={setTicker}/>}
 {page==='Opportunities'&&<><div className="toolbar"><form onSubmit={e=>{e.preventDefault();const requested=asset.toUpperCase();setTicker(requested);void run(`UC-03: analise ${requested} sob demanda, elegibilidade, risco, evidências e ranking canônico disponível.`,false,{ticker:requested,context:{selected_ticker:requested}})}}><label>Analisar ativo <input required value={asset} onChange={e=>setAsset(e.target.value)} placeholder="PETR4"/></label><button>Analisar</button></form><button onClick={()=>void run('UC-03: retorne ranking canônico B3, inclusive fora da carteira, score, risco, liquidez, evidências e as_of.')}>Buscar oportunidades</button></div><section className="panel"><h2>Ranking · risco × oportunidade</h2><p className="muted">Scores e classificação são mostrados somente quando fornecidos pelo pipeline canônico.</p><AnalysisOutput data={analysis}/><button onClick={()=>setPage('Strategy Lab')}>Comparar no Strategy Lab</button></section></>}
 {page==='Strategy Lab'&&<><section className="panel"><h2>Comparar alternativas</h2><form className="lab-form" onSubmit={e=>{e.preventDefault();const assetA=left.toUpperCase();const assetB=right.toUpperCase();const optionTextA=optionTypeForStrategy(strategyA)&&optionA?` contrato ${optionA}`:'';const optionTextB=optionTypeForStrategy(strategyB)&&optionB?` contrato ${optionB}`:'';const shocks=scenarioShocks.trim()?scenarioShocks.split(',').map(value=>Number(value.trim())):[];void run(`UC-04: compare ${strategyA} em ${assetA}${optionTextA} e ${strategyB} em ${assetB}${optionTextB}${amount?`, valor informado R$ ${amount}`:''}. Use cotações atuais OPLAB separadas do histórico. Mostre cenários, premissas e riscos canônicos; não atribua probabilidade aos choques.`,false,{ticker:null,context:{selected_ticker:null,comparison_assets:[assetA,assetB],strategy_a:strategyA,strategy_b:strategyB,option_a:optionTypeForStrategy(strategyA)?optionA:null,option_b:optionTypeForStrategy(strategyB)?optionB:null,comparison_amount:amount?Number(amount):null,scenario_horizon:scenarioHorizon||null,scenario_shocks_pct:scenarioHorizon?shocks:null}})}}><label>Ativo A<input required value={left} onChange={e=>setLeft(e.target.value)} placeholder="ITUB4"/></label><label>Estratégia A<select value={strategyA} onChange={e=>setStrategyA(e.target.value)}>{['Comprar ação','Vender/reduzir ação','Vender PUT','Vender CALL coberta','Manter'].map(x=><option key={x}>{x}</option>)}</select></label>{optionTypeForStrategy(strategyA)&&<label>{optionTypeForStrategy(strategyA)} A<select required value={optionA} onChange={e=>setOptionA(e.target.value)}><option value="">Selecione contrato OPLAB</option>{optionRowsA.map(row=><option key={row.contract.option_id} value={row.contract.option_id}>{row.contract.option_id} · Strike {brl(row.contract.strike)} · {row.contract.expiration_date} · Bid {brl(row.quote.bid)} · Ask {brl(row.quote.ask)} · Last {brl(row.quote.last)}</option>)}</select></label>}<label>Ativo B<input required value={right} onChange={e=>setRight(e.target.value)} placeholder="WEGE3"/></label><label>Estratégia B<select value={strategyB} onChange={e=>setStrategyB(e.target.value)}>{['Vender PUT','Vender CALL coberta','Vender/reduzir ação','Comprar ação','Manter'].map(x=><option key={x}>{x}</option>)}</select></label>{optionTypeForStrategy(strategyB)&&<label>{optionTypeForStrategy(strategyB)} B<select required value={optionB} onChange={e=>setOptionB(e.target.value)}><option value="">Selecione contrato OPLAB</option>{optionRowsB.map(row=><option key={row.contract.option_id} value={row.contract.option_id}>{row.contract.option_id} · Strike {brl(row.contract.strike)} · {row.contract.expiration_date} · Bid {brl(row.quote.bid)} · Ask {brl(row.quote.ask)} · Last {brl(row.quote.last)}</option>)}</select></label>}<label>Valor a simular em R$ {strategyA==='Vender/reduzir ação'||strategyB==='Vender/reduzir ação'?'(obrigatório para redução)':'(opcional)'}<input type="number" min="0" required={strategyA==='Vender/reduzir ação'||strategyB==='Vender/reduzir ação'} value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Horizonte comum dos cenários<input type="date" value={scenarioHorizon} onChange={e=>setScenarioHorizon(e.target.value)}/></label><label>Choques de preço em % (separados por vírgula)<input value={scenarioShocks} onChange={e=>setScenarioShocks(e.target.value)} placeholder="-10, 0, 10"/></label><button>Comparar</button><p className="muted">Sem horizonte, a comparação fundamental continua disponível sem payoff projetado. Para opções, o horizonte precisa coincidir com o vencimento. Choques são hipóteses suas, não previsões ou probabilidades. PUT usa 1 contrato cash-secured e o bid atual; CALL exige cobertura na carteira. Reduzir ação usa valor nocional e não infere quantidade executável, impostos, taxas ou slippage.</p></form></section><section className="panel"><h2>Comparação</h2><p className="muted">P&amp;L por cenário, quando solicitado, não escolhe um vencedor nem substitui sua tolerância a risco.</p><AnalysisOutput data={analysis}/></section></>}
 {page==='Market Intelligence'&&<><div className="workspace-tabs"><button className={!assetView?'selected':''} onClick={()=>setAssetView(false)}>Contexto de mercado</button><button className={assetView?'selected':''} onClick={()=>setAssetView(true)}>Análise de ativo</button></div>{!assetView?<section className="panel"><h2>Regime, fatores e eventos</h2><button onClick={()=>void run('UC-05/06/10: regime, drivers, taxas, câmbio, fluxo, fatores e eventos com data, qualidade e fontes; associação não é causalidade.')}>Analisar contexto</button><AnalysisOutput data={analysis}/></section>:<><div className="toolbar"><form onSubmit={e=>{e.preventDefault();void inspect(asset)}}><label>Ativo B3 <input required value={asset} onChange={e=>setAsset(e.target.value)} placeholder="PETR4"/></label><button>Analisar</button></form><div>{['1W','1M','3M','6M','1Y','Tudo'].map(h=><button key={h} className={h===horizon?'selected':''} onClick={()=>setHorizon(h)}>{h}</button>)}</div></div><div className="cards"><div className="metric"><span>Ativo</span><strong>{ticker||'—'}</strong><small>{when(live?.as_of)}</small></div><div className="metric"><span>Último preço</span><strong>{brl(live?.market.latest.close)}</strong><small>{when(live?.market.latest.observation_timestamp)}</small></div><div className="metric"><span>Volume</span><strong>{live?.market.latest.volume??'—'}</strong><small>{live?.market.latest.source||'Fonte indisponível'}</small></div></div><section className="panel"><h2>Preço e indicadores · {horizon}</h2><p className="muted">{live?`${live.market.history_count} registros no backend; série histórica e indicadores técnicos ainda não expostos por esta API.`:'Selecione um ativo.'}</p></section><section className="panel"><h2>Inteligência integrada · B3 + João + mercado</h2>{busy&&!analysis&&<p className="muted" role="status">Síntese em andamento. Evidências disponíveis aparecem assim que chegam.</p>}{!analysis&&<PersonalHistory value={personalHistory}/>}<AnalysisOutput data={analysis}/></section><section className="panel"><h2>Fundamentos e alvos institucionais</h2><p className="muted">Indisponíveis até fontes verificadas com instituição, data e referência. Nenhum preço alvo é estimado.</p></section><section className="panel"><h2>Piloto de inteligência · DeepSeek + OpenClaw</h2>{pilot?.status==='NOT_AVAILABLE'?<p className="muted">Ainda não há análise do lote de 20 ações para este ativo.</p>:pilot?.evidence?<><p className="muted">Evidências coletadas em {when(pilot.evidence.collected_at)}{pilot.evidence.latest_market_record?` · Cotação de ${when(pilot.evidence.latest_market_record.observation_timestamp)}`: ''} · {pilot.evidence.source_refs.length} referências</p><div className="llm-columns"><div><h3>DeepSeek local · {pilot.deepseek_status||'pendente'}</h3><p>{pilot.deepseek?.analysis||pilot.deepseek_error||'Aguardando execução.'}</p></div><div><h3>OpenClaw / ChatGPT · {pilot.openclaw_status||'pendente'}</h3><p>{pilot.openclaw?.analysis.summary||pilot.openclaw_error||'Aguardando execução.'}</p>{pilot.openclaw?.analysis.risks?.length?<details><summary>Riscos</summary><ul>{pilot.openclaw.analysis.risks.map((r,i)=><li key={i}>{r}</li>)}</ul></details>:null}{pilot.openclaw?.analysis.limitations?.length?<details><summary>Limitações</summary><ul>{pilot.openclaw.analysis.limitations.map((r,i)=><li key={i}>{r}</li>)}</ul></details>:null}</div></div><details><summary>Fontes usadas ({pilot.evidence.source_refs.length})</summary>{pilot.evidence.source_refs.map((ref,i)=><p key={i}>{ref}</p>)}</details></>:<p className="muted">Selecione um ativo para consultar o piloto.</p>}</section><section className="panel"><h2>Notícias e eventos</h2>{news?.events.length?news.events.map((v,i)=><details key={i}><summary>Evento {i+1}</summary><pre>{JSON.stringify(v,null,2)}</pre></details>):<p className="muted">Nenhuma notícia verificada disponível.</p>}</section></>}</>}
 </main><aside className="copilot"><div className="copilot-head"><strong>Copilot</strong><span className={online?'online-dot':'offline-dot'}>●</span></div><p className="context">Contexto: {ticker?`${ticker} / `:''}{page}{assetView&&page==='Market Intelligence'?' / Ativo':''}</p><button disabled={busy} onClick={()=>void run(`Faça um panorama de ${page}${ticker?` para ${ticker}`:''}; fatos, riscos, contradições, limitações e fontes.`,true)}>Visão geral</button><div className="conversation">{chat.map((c,i)=><div className="answer-card" key={i}><b>Você: {c.q}</b>{c.error?<div className="state-banner error"><strong>Erro no runtime</strong><span>{c.error}</span></div>:c.r?<AnalysisOutput data={c.r}/>:<p className="muted" role="status">Analisando no runtime B3…</p>}</div>)}</div><form className="chat-form" onSubmit={e=>{e.preventDefault();if(question.trim())void run(question.trim(),true)}}><textarea value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Pergunte sobre a seleção atual…" rows={4}/><button disabled={busy||!question.trim()}>Enviar</button></form></aside></div>
 {settings&&<div className="modal-backdrop" onClick={()=>setSettings(false)}><div className="transaction-modal" onClick={e=>e.stopPropagation()}><h2>Servidor Ubuntu · API B3</h2><form className="transaction-form" onSubmit={async(e:FormEvent)=>{e.preventDefault();try{setApiBaseUrl(url);setSettings(false);setPortfolio(null);setCapital(null);await load()}catch(x){setNotice(err(x))}}}><label>IP ou hostname e porta</label><input value={url} onChange={e=>setUrl(e.target.value)} placeholder="http://ubuntu:8000"/><small>{url}</small><button>Salvar e testar conexão</button></form><button onClick={()=>setSettings(false)}>Fechar</button></div></div>}
 {capitalEdit&&<div className="modal-backdrop" onClick={()=>setCapitalEdit(false)}><div className="transaction-modal" onClick={e=>e.stopPropagation()}><h2>Capital BTG</h2><form className="transaction-form" onSubmit={async(e:FormEvent)=>{e.preventDefault();try{const c=await b3Api.saveCapital(Number(available),Number(reserve));setCapital(c);setCapitalEdit(false);setNotice('Capital salvo no backend.')}catch(x){setNotice(err(x))}}}><label>Capital disponível (R$)</label><input type="number" min="0" step="0.01" required value={available} onChange={e=>setAvailable(e.target.value)}/><label>Reserva mínima (R$)</label><input type="number" min="0" step="0.01" required value={reserve} onChange={e=>setReserve(e.target.value)}/><button>Salvar no backend</button></form><button onClick={()=>setCapitalEdit(false)}>Fechar</button></div></div>}
 </div>;
}
