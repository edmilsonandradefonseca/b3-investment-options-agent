import {useState} from 'react';
import {b3Api} from './api/client';
import type {BrokerageOperation,PortfolioPosition,CurrentOptionRow,OrchestrateResponse,PortfolioSnapshot} from './api/contracts';
import {money,rows,obj,percent,date,Metric,State,Source} from './components/cockpit';

type ClosedOptionCycle={ticker:string;underlying:string;kind:'PUT'|'CALL'|'UNKNOWN';month:string;cash:number;trades:number;quantity:number;broker:string};
type MonthlyStockFlow={ticker:string;month:string;cash:number;trades:number};
function monthlyStockFlows(operations:BrokerageOperation[]):MonthlyStockFlow[]{
 const grouped=new Map<string,MonthlyStockFlow>();
 for(const op of operations){
  if(op.instrument_type!=='STOCK'||op.cash_flow==null||!Number.isFinite(op.cash_flow)||!op.trade_date)continue;
  const ticker=op.option_ticker.toUpperCase(),month=op.trade_date.slice(0,7),key=`${ticker}|${month}`;
  const current=grouped.get(key)||{ticker,month,cash:0,trades:0};
  current.cash+=op.cash_flow;current.trades+=1;grouped.set(key,current);
 }
 return [...grouped.values()].sort((a,b)=>a.month.localeCompare(b.month)||a.ticker.localeCompare(b.ticker));
}
const optionClass=(ticker:string):'PUT'|'CALL'|'UNKNOWN'=>{const c=ticker.toUpperCase()[4]||'';return c>='A'&&c<='L'?'CALL':c>='M'&&c<='X'?'PUT':'UNKNOWN'};
type MonthlyOptionFlow={underlying:string;kind:'PUT'|'CALL'|'UNKNOWN';month:string;cash:number;trades:number};
function monthlyOptionFlows(operations:BrokerageOperation[],knownAssets:string[]):MonthlyOptionFlow[]{
 const grouped=new Map<string,MonthlyOptionFlow>();
 for(const op of operations){
  if(op.instrument_type==='STOCK'||op.cash_flow==null||!Number.isFinite(op.cash_flow)||!op.trade_date)continue;
  const root=op.option_ticker.slice(0,4).toUpperCase();
  const matches=knownAssets.filter(t=>t.toUpperCase().startsWith(root));
  const underlying=matches.length===1?matches[0]:root;
  const kind=optionClass(op.option_ticker),month=op.trade_date.slice(0,7),key=`${underlying}|${kind}|${month}`;
  const current=grouped.get(key)||{underlying,kind,month,cash:0,trades:0};
  current.cash+=op.cash_flow;current.trades+=1;grouped.set(key,current);
 }
 return [...grouped.values()].sort((a,b)=>a.month.localeCompare(b.month)||a.underlying.localeCompare(b.underlying)||a.kind.localeCompare(b.kind));
}
function closedOptionCycles(operations:BrokerageOperation[],knownAssets:string[]):ClosedOptionCycle[]{
 const groups=new Map<string,BrokerageOperation[]>();
 for(const op of operations){if(op.instrument_type==='STOCK')continue;const key=`${op.broker}|${op.option_ticker}`;groups.set(key,[...(groups.get(key)||[]),op])}
 const out:ClosedOptionCycle[]=[];
 for(const rows of groups.values()){
  rows.sort((a,b)=>String(a.trade_date).localeCompare(String(b.trade_date))||a.transaction_id.localeCompare(b.transaction_id));
  let balance=0,cash=0,count=0,qty=0,openMonth='',daySides=new Set<string>(),lastDay='';
  const reset=()=>{balance=0;cash=0;count=0;qty=0;openMonth='';daySides=new Set<string>();lastDay=''};
  for(const op of rows){
   if(op.cash_flow==null||!Number.isFinite(op.cash_flow)||!(op.quantity>0)){reset();continue}
   const day=String(op.trade_date||'').slice(0,10),delta=op.side==='BUY'?op.quantity:-op.quantity;
   if(balance===0){openMonth=day.slice(0,7);cash=0;count=0;qty=0;daySides=new Set();lastDay=''}
   if(day!==lastDay){daySides=new Set();lastDay=day}
   daySides.add(op.side);
   const next=balance+delta;
   if(balance!==0&&Math.sign(next)!==Math.sign(balance)&&next!==0){reset();continue}
   balance=next;cash+=op.cash_flow;count++;qty=Math.max(qty,op.quantity);
   if(Math.abs(balance)<1e-8){
    const sameDayRows=rows.filter(x=>String(x.trade_date||'').slice(0,10)===day);
    const sides=new Set(sameDayRows.map(x=>x.side));
    const sameDayBothSides=sides.size>1;
    if(count>1&&!sameDayBothSides&&day){
     const root=op.option_ticker.slice(0,4).toUpperCase();
     const matches=knownAssets.filter(t=>t.toUpperCase().startsWith(root));
     const underlying=matches.length===1?matches[0]:root;
     out.push({ticker:op.option_ticker,underlying,kind:optionClass(op.option_ticker),month:day.slice(0,7),cash,trades:count,quantity:qty,broker:op.broker});
    }
    reset();
   }
  }
 }
 return out.sort((a,b)=>a.month.localeCompare(b.month)||a.underlying.localeCompare(b.underlying)||a.ticker.localeCompare(b.ticker));
}
function MonthlyBars({values,title,aria}:{values:Array<[string,number]>;title:string;aria:string}){
 const max=Math.max(1,...values.map(([,v])=>Math.abs(v))),zero=110;
 return <div className="panel" role="group" aria-label={aria}>
  <h3>{title}</h3>
  <svg viewBox="0 0 900 250" role="img" aria-label={aria} style={{width:'100%',height:'auto'}}>
   <line x1="30" x2="880" y1={zero} y2={zero} stroke="currentColor" opacity=".5"/>
   {values.map(([m,v],i)=>{const slot=820/values.length,x=45+i*slot,w=Math.max(8,slot*.55),h=Math.abs(v)/max*85;return <g key={m}><rect x={x} y={v>=0?zero-h:zero} width={w} height={Math.max(1,h)} fill={v>=0?'#24a36a':'#e05d5d'}><title>{m}: {money(v)}</title></rect><text x={x+w/2} y="224" textAnchor="middle" fontSize="11" fill="currentColor">{m.slice(5)}/{m.slice(0,4)}</text></g>})}
  </svg>
 </div>;
}
function ResultsPanel({cycles,optionFlows,stockFlows,ledgerAvailable}:{cycles:ClosedOptionCycle[];optionFlows:MonthlyOptionFlow[];stockFlows:MonthlyStockFlow[];ledgerAvailable:boolean}){
 const [asset,setAsset]=useState(''),[kind,setKind]=useState(''),[month,setMonth]=useState('');
 const assets=[...new Set([...optionFlows.map(x=>x.underlying),...cycles.map(x=>x.underlying),...stockFlows.map(x=>x.ticker)])].sort();
 const months=[...new Set([...optionFlows.map(x=>x.month),...cycles.map(x=>x.month),...stockFlows.map(x=>x.month)])].sort();
 const visibleFlows=optionFlows.filter(x=>(!asset||x.underlying===asset)&&(!kind||kind==='PUT'||kind==='CALL'?(!kind||x.kind===kind):true)&&(!month||x.month===month));
 const visible=cycles.filter(x=>kind!=='STOCK'&&(!asset||x.underlying===asset)&&(!kind||x.kind===kind)&&(!month||x.month===month));
 const visibleStocks=stockFlows.filter(x=>(!asset||x.ticker===asset)&&(!kind||kind==='STOCK')&&(!month||x.month===month));
 const optionByMonth=new Map<string,number>(),stockByMonth=new Map<string,number>();
 for(const x of visibleFlows)optionByMonth.set(x.month,(optionByMonth.get(x.month)||0)+x.cash);
 for(const x of visibleStocks)stockByMonth.set(x.month,(stockByMonth.get(x.month)||0)+x.cash);
 const optionValues=[...optionByMonth.entries()].sort(([a],[b])=>a.localeCompare(b));
 const stockValues=[...stockByMonth.entries()].sort(([a],[b])=>a.localeCompare(b));
 return <section className="panel">
  <h2>Resultado por ativo e mês</h2>
  <p className="muted">Opções: fluxo líquido de compras e vendas no mês da nota, inclusive contratos ainda abertos; não é lucro realizado. Ações: fluxo de caixa mensal das notas; não é lucro realizado sem custo de aquisição. Os custos e tributos da nota ainda não foram conciliados.</p>
  {!ledgerAvailable?<State kind="limited" title="Notas de corretagem indisponíveis">Importe as notas para calcular os resultados.</State>:null}
  <div className="inline-controls">
   <label>Ativo<select aria-label="Filtrar resultado por ativo" value={asset} onChange={e=>setAsset(e.target.value)}><option value="">Todos</option>{assets.map(x=><option key={x}>{x}</option>)}</select></label>
   <label>Tipo<select aria-label="Filtrar resultado por tipo" value={kind} onChange={e=>setKind(e.target.value)}><option value="">Ação, PUT e CALL</option><option value="STOCK">AÇÃO</option><option value="PUT">PUT</option><option value="CALL">CALL</option><option value="UNKNOWN">Tipo não identificado</option></select></label>
   <label>Mês<select aria-label="Filtrar resultado por mês" value={month} onChange={e=>setMonth(e.target.value)}><option value="">Todos</option>{months.map(x=><option key={x}>{x}</option>)}</select></label>
  </div>
  {optionValues.length>0&&kind!=='STOCK'&&<MonthlyBars values={optionValues} title="Opções · fluxo líquido das notas por mês" aria="Gráfico mensal de fluxo de caixa de opções"/>}
  {stockValues.length>0&&(!kind||kind==='STOCK')&&<MonthlyBars values={stockValues} title="Ações · fluxo líquido de caixa por mês" aria="Gráfico mensal do fluxo de caixa das ações"/>}
  {kind!=='STOCK'&&<div className="table-wrap"><h3>Ciclos de opções encerrados</h3><table><thead><tr><th>Ativo-base</th><th>Contrato</th><th>Tipo</th><th>Mês do encerramento</th><th>Quantidade pareada</th><th>Lançamentos</th><th>Saldo bruto</th></tr></thead><tbody>
   {visible.map((x,i)=><tr key={x.ticker+':'+x.month+':'+i}><td>{x.underlying}</td><td>{x.ticker}</td><td>{x.kind==='UNKNOWN'?'Não identificado':x.kind}</td><td>{x.month}</td><td>{x.quantity}</td><td>{x.trades}</td><td>{money(x.cash)}</td></tr>)}
  </tbody></table></div>}
  {(!kind||kind==='STOCK')&&<div className="table-wrap"><h3>Operações com ações · fluxo de caixa</h3><table><thead><tr><th>Ativo</th><th>Mês</th><th>Negócios</th><th>Saldo de caixa (vendas − compras)</th></tr></thead><tbody>
   {visibleStocks.map((x,i)=><tr key={x.ticker+':'+x.month+':'+i}><td>{x.ticker}</td><td>{x.month}</td><td>{x.trades}</td><td>{money(x.cash)}</td></tr>)}
  </tbody></table></div>}
  {visible.length===0&&visibleFlows.length===0&&visibleStocks.length===0&&<State kind={ledgerAvailable?'limited':'loading'} title={ledgerAvailable?'Nenhum resultado compatível com os filtros':'Carregando dados'}>{ledgerAvailable?'Confira os filtros ou importe notas com operações pareadas. Posições abertas não entram no resultado dos ciclos de opções.':''}</State>}
  <p className="muted">A tabela de ciclos lista contratos de opção pareados até quantidade zero. Ações mostram fluxo de caixa, sem inferir preço de custo de posições anteriores ao período importado. Custos e tributos seguem pendentes de conciliação.</p>
 </section>;
}

type Props={positions:PortfolioPosition[];operations:BrokerageOperation[];ledgerAvailable:boolean;onSelect:(ticker:string,underlying?:string)=>void;portfolio:PortfolioSnapshot|null;pnl:OrchestrateResponse|null;result?:OrchestrateResponse|null};
export default function OptionsWorkspace({positions,operations,ledgerAvailable,onSelect,result,portfolio,pnl}:Props){
 const [tab,setTab]=useState('Posições'),[query,setQuery]=useState(''),[kind,setKind]=useState(''),[underlying,setUnderlying]=useState(''),[chain,setChain]=useState<CurrentOptionRow[]>([]),[loading,setLoading]=useState(false),[error,setError]=useState(''),[asOf,setAsOf]=useState(''),[page,setPage]=useState(0);
 const knownAssets=(portfolio?.positions||[]).flatMap(p=>p.instrument_type==='STOCK'?[p.ticker]:p.underlying_ticker?[p.underlying_ticker]:[]);
 const completedCycles=closedOptionCycles(operations,knownAssets),optionFlows=monthlyOptionFlows(operations,knownAssets),stockFlows=monthlyStockFlows(operations);
 const visible=positions.filter(p=>(!kind||p.option_type===kind)&&p.ticker.toLowerCase().includes(query.toLowerCase()));
 const notes=operations.filter(o=>o.option_ticker.toLowerCase().includes(query.toLowerCase()));
 const canonical=rows(result?.result.option_positions),intelligence=obj(portfolio?.intelligence),risk=obj(intelligence.capital_risk),assessments=rows(intelligence.assessments);
 const [selected,setSelected]=useState('');const detail=positions.find(p=>p.ticker===selected),assessment=assessments.find(r=>r.position_id===detail?.position_id),pnlRow=rows(pnl?.result.position_pnl).find(r=>r.position_id===detail?.position_id),exposure=rows(intelligence.exposures).find(r=>r.ticker===detail?.underlying_ticker);
 async function fetchChain(){setLoading(true);setError('');try{const r=await b3Api.currentOptions(underlying,kind==='CALL'?'CALL':'PUT',150);setChain(r.options);setAsOf(r.as_of)}catch(e){setError(e instanceof Error?e.message:String(e));setChain([])}finally{setLoading(false)}}
 return <div className="options-workspace"><div className="cards"><Metric label="Posições abertas no snapshot" value={positions.length}/><Metric label="Capital para exercício de PUTs" value={money(risk.assignment_capital)}/><Metric label="Ações CALL sem cobertura" value={String(risk.uncovered_call_shares??'Indisponível')}/></div><Source asOf={portfolio?.as_of} source={portfolio?.source_refs?.join(' · ')}/><div className="workspace-tabs" role="tablist">{['Posições','Cadeia de opções','Execuções','Resultados'].map(t=><button role="tab" aria-selected={tab===t} className={tab===t?'selected':''} key={t} onClick={()=>setTab(t)}>{t}</button>)}</div><div className="toolbar"><label>Buscar contrato<input aria-label="Buscar contrato" value={query} onChange={e=>{setQuery(e.target.value);setPage(0)}} placeholder="PETR…"/></label>{tab==='Posições'&&<label>Tipo<select value={kind} onChange={e=>setKind(e.target.value)}><option value="">PUT e CALL</option><option>PUT</option><option>CALL</option></select></label>}</div>
 {tab==='Posições'&&<section className="panel"><div className="section-head"><h2>Posições abertas ({visible.length})</h2><span className="badge">Snapshot BTG</span></div><div className="table-wrap"><table><thead><tr>{['Ativo','Contrato','Tipo','Direção','Quantidade','Strike','Vencimento','DTE no snapshot','Custo médio snapshot','Preço snapshot','Valor snapshot'].map(s=><th key={s}>{s}</th>)}</tr></thead><tbody>{visible.map(p=><tr key={p.position_id}><td>{p.underlying_ticker??'Indisponível'}</td><td><button className="text-button" onClick={()=>{setSelected(p.ticker);onSelect(p.ticker,p.underlying_ticker??undefined)}}>{p.ticker}</button></td><td>{p.option_type}</td><td>{p.quantity<0?'Vendida':'Comprada'}</td><td>{p.quantity}</td><td>{money(p.strike)}</td><td>{p.expiration_date??'Indisponível'}</td><td>{String(canonical.find(r=>r.position_id===p.position_id)?.dte??'Indisponível')}</td><td>{money(p.average_cost)}</td><td>{money(p.market_price)}</td><td>{money(p.market_value)}</td></tr>)}</tbody></table></div>{!visible.length&&<State title="Nenhuma posição para este filtro">Ajuste os filtros ou importe o snapshot de opções.</State>}</section>}
 {tab==='Posições'&&detail&&<section className="panel"><div className="section-head"><h2>{detail.ticker} · posição e obrigações</h2><button className="ghost" onClick={()=>setSelected('')}>Fechar detalhe</button></div><div className="cards"><Metric label="Capital de assignment" value={money(assessment?.assignment_capital)}/><Metric label="Ações a entregar" value={String(assessment?.deliverable_shares??'Indisponível')}/><Metric label="Cobertura CALL por ativo" value={percent(exposure?.call_coverage_ratio)}/><Metric label="P&L não realizado no snapshot" value={money(pnlRow?.unrealized_pnl)}/></div><Source asOf={portfolio?.as_of} source={detail.source_ref}/><State kind="limited" title="Moneyness e métricas live">IV, Greeks e moneyness desta posição não vieram no snapshot. Consulte a cadeia atual; cotações com outra data não são reconciliadas silenciosamente com o snapshot.</State></section>}
 {tab==='Cadeia de opções' &&<section className="panel"><h2>Cotações e Greeks fornecidos pela OPLAB</h2><form className="inline-controls" onSubmit={e=>{e.preventDefault();void fetchChain()}}><label>Ativo<input required aria-label="Ativo da cadeia" value={underlying} onChange={e=>setUnderlying(e.target.value.toUpperCase())} placeholder="VALE3" pattern="[A-Z]{4}[0-9]{1,2}"/></label><label>Tipo<select value={kind||'PUT'} onChange={e=>setKind(e.target.value)}><option>PUT</option><option>CALL</option></select></label><button disabled={loading}>Consultar cadeia</button></form>{loading&&<State kind="loading" title="Consultando opções">Aguardando o provedor.</State>}{error&&<State kind="error" title="Cadeia indisponível">{error}</State>}<Source asOf={asOf} source="OPLAB"/><div className="table-wrap"><table><thead><tr>{['Contrato','Strike','Vencimento','Bid','Ask','Último','IV','Delta','Gamma','Theta','Vega','Volume','OI'].map(s=><th key={s}>{s}</th>)}</tr></thead><tbody>{chain.filter(r=>r.contract.option_id.toLowerCase().includes(query.toLowerCase())).map(r=><tr key={r.contract.option_id}><td><button className="text-button" onClick={()=>onSelect(r.contract.option_id)}>{r.contract.option_id}</button></td><td>{money(r.contract.strike)}</td><td>{r.contract.expiration_date}</td><td>{money(r.quote.bid)}</td><td>{money(r.quote.ask)}</td><td>{money(r.quote.last)}</td>{['implied_volatility','delta','gamma','theta','vega','volume','open_interest'].map(k=><td key={k}>{k==='implied_volatility'?percent(r.quote.implied_volatility):String(r.quote[k as keyof typeof r.quote]??'Indisponível')}</td>)}</tr>)}</tbody></table></div>{!chain.length&&!loading&&!error&&<State title="Escolha um ativo e consulte a cadeia">Nenhuma cotação foi carregada.</State>}</section>}
 {tab==='Execuções'&&<section className="panel"><h2>Execuções observadas ({notes.length})</h2><p className="muted">Fluxo recebido/pago na nota; não é lucro realizado. Vínculo com o ativo e fechamento não são inferidos.</p>{!ledgerAvailable&&<State kind="limited" title="Ledger indisponível">Importe notas de corretagem para reconstruir a história.</State>}<div className="table-wrap"><table><thead><tr>{['Data','Contrato','Direção','Quantidade','Preço','Fluxo bruto','Nota / fonte'].map(s=><th key={s}>{s}</th>)}</tr></thead><tbody>{notes.slice(page*30,page*30+30).map(o=><tr key={o.transaction_id}><td>{date(o.trade_date)}</td><td><button className="text-button" onClick={()=>onSelect(o.option_ticker)}>{o.option_ticker}</button></td><td>{o.side==='SELL'?'Venda':'Compra'}</td><td>{o.quantity}</td><td>{money(o.execution_price)}</td><td>{money(o.cash_flow)}</td><td><details><summary>{o.note_number??'Fonte'}</summary>{o.source_ref}</details></td></tr>)}</tbody></table></div><div className="pagination"><button disabled={!page} onClick={()=>setPage(page-1)}>Anterior</button><span>Página {page+1}</span><button disabled={(page+1)*30>=notes.length} onClick={()=>setPage(page+1)}>Próxima</button></div>{!notes.length&&ledgerAvailable&&<State title="Nenhuma execução para este filtro">Ajuste a busca ou carregue notas.</State>}</section>}
 {tab==='Resultados'&&<ResultsPanel cycles={completedCycles} optionFlows={optionFlows} stockFlows={stockFlows} ledgerAvailable={ledgerAvailable}/ >}</div>;
}
