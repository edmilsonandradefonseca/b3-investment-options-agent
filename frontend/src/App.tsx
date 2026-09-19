import { FormEvent, useEffect, useMemo, useState, type ReactNode } from "react";

type Page = "Portfolio" | "Options" | "Opportunities" | "Portfolio Intelligence" | "Knowledge";
type Position = { ticker:string; qty:string; avg:number; price:number; value:number; pnl:number; pct:number };

const API_BASE = import.meta.env.VITE_ORCHESTRATOR_URL ?? "http://127.0.0.1:8000";

const nav: { id: Page; icon: string; subtitle: string }[] = [
  { id:"Portfolio", icon:"▥", subtitle:"Posições e visão geral" },
  { id:"Options", icon:"◈", subtitle:"Greeks, risco e operações" },
  { id:"Opportunities", icon:"◎", subtitle:"Ideias e sinais" },
  { id:"Portfolio Intelligence", icon:"◇", subtitle:"Análises e recomendações" },
  { id:"Knowledge", icon:"▱", subtitle:"Pesquisa e contexto" },
];

const positions: Position[] = [
  {ticker:"PETR4",qty:"2.000",avg:34.10,price:37.20,value:74400,pnl:6200,pct:9.1},
  {ticker:"VALE3",qty:"1.000",avg:55.80,price:62.15,value:62150,pnl:6350,pct:11.4},
  {ticker:"ITUB4",qty:"800",avg:54.20,price:60.40,value:48320,pnl:4960,pct:11.4},
  {ticker:"BBDC4",qty:"2.000",avg:13.80,price:14.45,value:28910,pnl:1300,pct:4.7},
  {ticker:"BBAS3",qty:"1.000",avg:24.50,price:24.56,value:24560,pnl:60,pct:.2},
];

const history = [321800,326900,333800,337200,334900,342500,346900,351200,348800,355100,361400,372480];
const allocation = [
  {label:"Ações",value:82,color:"#1684ff"},
  {label:"Opções (Long)",value:12.5,color:"#19d59a"},
  {label:"Opções (Short)",value:5.5,color:"#ff9d4d"},
];

function infer_b3_option_type(ticker:string){const s=ticker.replace(/\s+/g,"").toUpperCase(); const m=s.match(/[A-Z]$/); if(!m)return null; return "ABCDEFGHIJKL".includes(m[0])?"CALL":"MNOPQRSTUVWX".includes(m[0])?"PUT":null;} function pct(v:number){return (v.toFixed(1).replace(".",",")+"%")} function money(v:number){ return new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:0}).format(v); }

function Metric({title,value,detail,icon}:{title:string;value:string;detail:string;icon:string}) {
  return <div className="metric"><div className="metric-top"><span>{title}</span><b className="metric-icon">{icon}</b></div><strong>{value}</strong><small className={detail.startsWith("▲") ? "positive" : ""}>{detail}</small></div>;
}

function Sidebar({page,setPage}:{page:Page;setPage:(p:Page)=>void}) {
  return <aside className="sidebar">
    <div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Seu copiloto de investimentos com IA</small></div></div>
    <nav>{nav.map(n=><button key={n.id} className={"nav-item "+(page===n.id?"active":"")} onClick={()=>setPage(n.id)}><span className="nav-icon">{n.icon}</span><span><strong>{n.id}</strong><small>{n.subtitle}</small></span></button>)}</nav>
    <section className="connections"><label>DADOS & CONEXÕES</label>
      <div className="connection"><b>BTG Portfolio</b><span className="status">● Carregado</span><small>Snapshot persistido</small></div>
      <div className="connection"><b>Options Transactions</b><span className="status">● Carregado</span><small>Histórico persistido</small></div>
      <div className="connection"><b>Reconciliação</b><span className="status">● OK</span><small>Sem divergências críticas</small></div>
      <label className="load">↥ &nbsp; Carregar arquivos Excel<input type="file" accept=".xlsx,.xlsm" hidden /></label>
    </section>
    <section className="knowledge-status"><label>BASE DE CONHECIMENTO</label><span>◈ Obsidian <i>Conectado</i></span><span>◉ RAG (Qdrant) <i>Conectado</i></span><span>● Neo4j <i>Conectado</i></span></section>
    <footer>v1.0 React · B3 Investment Copilot</footer>
  </aside>;
}

function Copilot({setPage}:{setPage:(p:Page)=>void}) {
  const [question,setQuestion]=useState(""); const [answer,setAnswer]=useState(""); const [asking,setAsking]=useState(false);
  async function ask(e:FormEvent){e.preventDefault(); if(!question.trim()||asking)return; setAsking(true); try{const r=await fetch(API_BASE+"/orchestrate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task:question.trim(),context:{client:"react-desktop"}})}); const d=await r.json(); if(!r.ok)throw new Error(d.detail??"Falha no orquestrador"); setAnswer(d.result?.answer??d.result?.summary??JSON.stringify(d.result,null,2));}catch(err){setAnswer("Orquestrador indisponível: "+(err instanceof Error?err.message:"erro"));}finally{setAsking(false);}}
  const examples=["Quais opções de PETR4 eu rolei?","Qual é meu resultado acumulado com opções?","Onde estou ganhando e perdendo?","Como está meu risco de carteira?"];
  return <aside className="copilot"><div className="copilot-head"><div><strong>AI Copilot</strong><small>Seu time de agentes especialistas</small></div><span className="online-dot">● Online</span></div>
    <div className="agent-tabs"><button className="selected">Chat</button><button>Agentes</button><button>Histórico</button></div>
    <div className="copilot-intro"><h2>Olá, Edmilson! 👋</h2><p>Analise sua carteira, explore opções e faça drill-down até as transações.</p><ul><li>Analisar posições</li><li>Explorar rolagens</li><li>Explicar P&L acumulado</li><li>Pesquisar conhecimento</li></ul></div>
    <div className="suggestions"><b>Exemplos de perguntas</b>{examples.map(q=><button key={q} onClick={()=>{setQuestion(q); if(q.includes("PETR4"))setPage("Options")}}>{q}<span>›</span></button>)}</div>
    {answer&&<pre className="answer">{answer}</pre>}
    <form className="chat-form" onSubmit={ask}><select defaultValue="general"><option value="general">Investment Copilot (Geral)</option><option value="options">Options Agent</option><option value="risk">Risk Agent</option></select><textarea value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Digite sua pergunta aqui..." rows={4}/><button disabled={asking}>{asking?"…":"➤"}</button></form>
    <small className="disclaimer">Sem execução de ordens. Análises informativas.</small>
  </aside>;
}

function Portfolio() {
  type PortfolioData = {
    status: string;
    as_of?: string;
    quality_status?: string;
    cash?: number;
    summary?: { total_value:number; stock_value:number; option_value:number; position_count:number };
    positions?: Array<{ticker:string; instrument_type:string; quantity:number; average_cost:number|null; market_price:number|null; market_value:number|null; pnl:number|null; pnl_pct:number|null; option_type:string|null; underlying_ticker:string|null; strike:number|null; expiration_date:string|null}>;
    message?: string;
  };
  const [data,setData]=useState<PortfolioData|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");

  useEffect(()=>{
    fetch(API_BASE+"/api/portfolio")
      .then(async r=>{const d=await r.json(); if(!r.ok) throw new Error(d.detail??"Falha ao carregar portfolio"); return d;})
      .then(d=>{setData(d); setError(d.status==="OK"?"":"Snapshot do portfolio não encontrado.");})
      .catch(err=>setError(err instanceof Error?err.message:"Falha ao carregar portfolio"))
      .finally(()=>setLoading(false));
  },[]);

  const positions=(data?.positions??[]).slice().sort((a,b)=>(b.market_value??0)-(a.market_value??0));
  const top=positions.slice(0,5);
  const summary=data?.summary;
  const total=summary?.total_value??0;
  const stockPct=total?((summary?.stock_value??0)/total*100):0;
  const longOptionValue=positions.filter(p=>p.instrument_type==="OPTION" && p.quantity>0).reduce((s,p)=>s+Math.abs(p.market_value??0),0);
  const shortOptionValue=positions.filter(p=>p.instrument_type==="OPTION" && p.quantity<0).reduce((s,p)=>s+Math.abs(p.market_value??0),0);
  const allocationItems=[
    {label:"Ações",value:summary?.stock_value??0,css:"#1684ff"},
    {label:"Opções (Long)",value:longOptionValue,css:"#19d59a"},
    {label:"Opções (Short)",value:shortOptionValue,css:"#ff9d4d"},
    {label:"Cash",value:Math.max(data?.cash??0,0),css:"#8a9bad"},
  ].filter(x=>x.value>0);
  const allocationTotal=allocationItems.reduce((s,x)=>s+x.value,0);
  let cursor=0;
  const donutStops=allocationItems.map(x=>{const startPct=allocationTotal?cursor/allocationTotal*100:0; cursor+=x.value; const endPct=allocationTotal?cursor/allocationTotal*100:0; return x.css+" "+startPct+"% "+endPct+"%";}).join(",");
  const optionPct=total?((summary?.option_value??0)/total*100):0;

  return <main className="workspace">
    <div className="workspace-head"><div><h1>Olá, Edmilson! 👋</h1><p>Visão real da carteira carregada do BTG.</p></div><span className="updated">{loading?"Carregando…":(data?.as_of?"Snapshot em "+data.as_of:"Sem snapshot")}</span></div>
    {error&&<div className="analytics-summary"><strong>Dados do Portfolio</strong><span>{data?.message??error}</span></div>}
    <section className="cards">
      <Metric title="Valor Total" value={summary?money(total):"—"} detail={summary?String(summary.position_count)+" posições":"Sem dados"} icon="↗"/>
      <Metric title="Cash" value={money(data?.cash??0)} detail="Fonte BTG" icon="◉"/>
      <Metric title="Ações" value={summary?money(summary.stock_value):"—"} detail={summary?stockPct.toFixed(1).replace(".",",")+"% da carteira":"Sem dados"} icon="▥"/>
      <Metric title="Opções (Valor Líquido)" value={summary?money(summary.option_value):"—"} detail={summary?optionPct.toFixed(1).replace(".",",")+"% da carteira":"Sem dados"} icon="◈"/>
    </section>
    <section className="grid-two">
      <Card title="Composição da Carteira">
        <div className="allocation">
          <div className="donut" style={{background:allocationTotal?("conic-gradient("+donutStops+")"):"#163951"}}><div className="donut-hole"><b>{money(allocationTotal)}</b><span>exposição bruta</span></div></div>
          <div className="legend">
            {allocationItems.map(item=><div key={item.label}><i style={{background:item.css}}/><span>{item.label}</span><b>{(allocationTotal?item.value/allocationTotal*100:0).toFixed(1).replace(".",",")}%</b></div>)}
          </div>
        </div>
      </Card>
      <Card title="Fonte dos dados">
        <div className="analytics-summary">
          <strong>{data?.quality_status??"—"}</strong>
          <span>Snapshot oficial carregado pelo BtgRendaVariavelLoader</span>
          <small>{data?.as_of?"Data-base: "+data.as_of:"Nenhum snapshot disponível."}</small>
        </div>
      </Card>
    </section>
    <section className="grid-two">
      <Card title="Top Posições">
        <table><thead><tr><th>Ativo</th><th>Qtd</th><th>Preço Médio</th><th>Atual</th><th>Valor (R$)</th><th>P&L</th><th>P&L %</th></tr></thead>
        <tbody>{top.map(p=><tr key={p.ticker}><td><strong>{p.ticker}</strong></td><td>{p.quantity.toLocaleString("pt-BR")}</td><td>{p.average_cost==null?"—":p.average_cost.toFixed(2)}</td><td>{p.market_price==null?"—":p.market_price.toFixed(2)}</td><td>{p.market_value==null?"—":p.market_value.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})}</td><td className={(p.pnl??0)>=0?"positive":"negative"}>{p.pnl==null?"—":money(p.pnl)}</td><td className={(p.pnl_pct??0)>=0?"positive":"negative"}>{p.pnl_pct==null?"—":(p.pnl_pct>=0?"+":"")+p.pnl_pct.toFixed(1).replace(".",",")+"%"}</td></tr>)}</tbody></table>
      </Card>
      <Card title="Todas as posições">
        <div className="table-wrap"><table><thead><tr><th>Ativo</th><th>Tipo</th><th>Qtd</th><th>Valor</th></tr></thead><tbody>{positions.map(p=><tr key={p.ticker}><td><strong>{p.ticker}</strong></td><td>{p.instrument_type}</td><td>{p.quantity.toLocaleString("pt-BR")}</td><td>{p.market_value==null?"—":money(p.market_value)}</td></tr>)}</tbody></table></div>
      </Card>
    </section>
  </main>;
}


function Options() {
  type Analytics = { summary?: { realized_pnl:number; premium_received:number; premium_paid:number; return_pct:number|null; lifecycle_count:number; profitable_lifecycles:number; losing_lifecycles:number }; lifecycles?: Array<{option_ticker:string; option_type:string|null; status:string; realized_pnl:number|null; first_trade_date:string|null; last_trade_date:string|null; transaction_count:number; history_completeness:string}>; transactions?: Array<{transaction_id:string; option_ticker:string; date:string|null; side:string; quantity:number; execution_price:number|null; total_amount:number|null; source_type:string; source_id:string|null; note_number:string|null}>; data_quality?: {status:string;transactions_included?:number;warning?:string;note?:string} };
  const [underlying,setUnderlying]=useState("Todos"), [type,setType]=useState("Todas"), [start,setStart]=useState("2026-05-01"), [end,setEnd]=useState("2026-09-30"), [data,setData]=useState<Analytics|null>(null), [status,setStatus]=useState("Clique em Atualizar análise");
  async function refresh(){ setStatus("Consultando ledger…"); try { const qs=new URLSearchParams({underlying,option_type:type,start_date:start,end_date:end}); const r=await fetch(API_BASE+"/api/options/analytics?"+qs.toString()); const d=await r.json(); if(!r.ok) throw new Error(d.detail??"Falha no endpoint"); setData(d); setStatus("Dados reais carregados"); } catch(err) { setStatus("Erro: "+(err instanceof Error?err.message:"falha")); setData(null); } }
  const s=data?.summary;
  return <main className="workspace options-page">
    <div className="workspace-head"><div><h1>Options Intelligence</h1><p>Resultado acumulado, rolagens e drill-down por papel.</p></div><span className="updated">{status}</span></div>
    <section className="filters"><label>Ativo<select value={underlying} onChange={e=>setUnderlying(e.target.value)}><option>Todos</option><option>PETR4</option><option>VALE3</option><option>ITUB4</option></select></label><label>Tipo<select value={type} onChange={e=>setType(e.target.value)}><option>Todas</option><option>CALL</option><option>PUT</option></select></label><label>Início<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Fim<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label><button className="primary-btn" onClick={refresh}>Atualizar análise</button></section>
    <section className="cards"><Metric title="P&L realizado acumulado" value={s?money(s.realized_pnl):"—"} detail={s?s.lifecycle_count+" lifecycles confirmados":"Sem consulta"} icon="Σ"/><Metric title="Prêmios recebidos" value={s?money(s.premium_received):"—"} detail={s?s.profitable_lifecycles+" positivos · "+s.losing_lifecycles+" negativos":"Sem consulta"} icon="↓"/><Metric title="Lifecycles" value={s?String(s.lifecycle_count):"—"} detail={data?.data_quality?.transactions_included?data.data_quality.transactions_included+" transações":"Sem consulta"} icon="↻"/><Metric title="Resultado %" value={s?.return_pct!=null?pct(s.return_pct):"—"} detail="Sobre a base de capital disponível" icon="%"/></section>
    <section className="grid-two"><Card title="P&L acumulado"><div className="analytics-summary"><strong>{s?money(s.realized_pnl):"—"}</strong><span>resultado realizado no período selecionado</span><small>{data?.data_quality?.warning??"Os dados são provenientes do ledger persistido."}</small></div></Card><Card title="Qualidade dos dados"><div className="analytics-summary"><strong>{data?.data_quality?.transactions_included??"—"}</strong><span>transações incluídas</span><small>{data?.data_quality?.status??"Ainda não consultado"}</small></div></Card></section>
    <Card title={(underlying==="Todos"?"Todos os ativos":underlying)+" — Lifecycles"}><div className="table-wrap"><table><thead><tr><th>Contrato</th><th>Tipo</th><th>Início</th><th>Fim</th><th>Status</th><th>Operações</th><th>P&L</th><th>Histórico</th></tr></thead><tbody>{(data?.lifecycles??[]).map(x=><tr key={x.option_ticker}><td><strong>{x.option_ticker}</strong></td><td>{x.option_type??"—"}</td><td>{x.first_trade_date??"—"}</td><td>{x.last_trade_date??"—"}</td><td>{x.status}</td><td>{x.transaction_count}</td><td className={(x.realized_pnl??0)>=0?"positive":"negative"}>{x.realized_pnl==null?"—":money(x.realized_pnl)}</td><td>{x.history_completeness}</td></tr>)}{!data?.lifecycles?.length&&<tr><td colSpan={8} className="table-empty">Nenhum lifecycle retornado para os filtros atuais.</td></tr>}</tbody></table></div></Card>
    <Card title="Drill-down — transações individuais"><div className="table-wrap"><table><thead><tr><th>Data</th><th>Contrato</th><th>Tipo</th><th>Lado</th><th>Qtd</th><th>Preço</th><th>Fluxo</th><th>Origem</th></tr></thead><tbody>{(data?.transactions??[]).map(x=><tr key={x.transaction_id}><td>{x.date??"—"}</td><td><strong>{x.option_ticker}</strong></td><td>{infer_b3_option_type(x.option_ticker)??"—"}</td><td className={x.side==="SELL"?"positive":"negative"}>{x.side}</td><td>{x.quantity}</td><td>{x.execution_price==null?"—":x.execution_price.toFixed(2)}</td><td>{x.total_amount==null?"—":money(x.total_amount)}</td><td>{x.source_type}{x.note_number?" · Nota "+x.note_number:""}</td></tr>)}{!data?.transactions?.length&&<tr><td colSpan={8} className="table-empty">Nenhuma transação retornada.</td></tr>}</tbody></table></div></Card>
  </main>
}


function Card({title,action,children}:{title:string;action?:ReactNode;children:ReactNode}){return <div className="panel"><div className="panel-title"><h2>{title}</h2>{action}</div>{children}</div>}

function App(){const [page,setPage]=useState<Page>("Portfolio"); return <div className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Seu copiloto de investimentos com IA</small></div></div><div className="search">⌕ <span>Buscar ativos, estratégias ou fazer uma pergunta...</span><kbd>Ctrl K</kbd></div><div className="market"><span>IBOV <b>134.521</b> <i>+1,2%</i></span><span>DÓLAR <b>4,92</b> <em>-0,3%</em></span><span>PETR4 <b>37,20</b> <i>+2,1%</i></span><span className="bell">♧</span><span className="avatar">EF</span><b>Edmilson⌄</b></div></header><div className="body"><Sidebar page={page} setPage={setPage}/><div>{page==="Portfolio"?<Portfolio/>:page==="Options"?<Options/>:<main className="workspace"><div className="workspace-head"><div><h1>{page}</h1><p>Workspace React preparado para o próximo módulo.</p></div></div><div className="panel placeholder"><h2>{page}</h2><p>O shell React já está pronto. Este módulo será conectado aos engines Python existentes sem duplicar a lógica de negócio.</p></div></main>}</div><Copilot setPage={setPage}/></div></div>}

export default App;
