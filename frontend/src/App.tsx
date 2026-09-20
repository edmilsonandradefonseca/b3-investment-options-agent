import { FormEvent, useEffect, useState, type ReactNode } from "react";

type Page = "Portfolio" | "Options" | "Reconciliation" | "Opportunities" | "Portfolio Intelligence" | "Knowledge" | "Copilot";
const nav: Array<{id: Page; icon: string; subtitle: string}> = [
  { id: "Portfolio", icon: "▣", subtitle: "Visão geral" },
  { id: "Options", icon: "◇", subtitle: "Opções & P&L" },
  { id: "Reconciliation", icon: "⇄", subtitle: "Excel × Notas" },
  { id: "Opportunities", icon: "✦", subtitle: "Oportunidades" },
  { id: "Portfolio Intelligence", icon: "◈", subtitle: "Exposição & risco" },
  { id: "Knowledge", icon: "◉", subtitle: "Conhecimento" },
  { id: "Copilot", icon: "✧", subtitle: "Pergunte ao Orchestrator" },
];

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

function pct(v:number){return (v.toFixed(1).replace(".",",")+"%")} function money(v:number){ return new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:0}).format(v); }

function Metric({title,value,detail,icon}:{title:string;value:string;detail:string;icon:string}) {
  return <div className="metric"><div className="metric-top"><span>{title}</span><b className="metric-icon">{icon}</b></div><strong>{value}</strong><small className={detail.startsWith("▲") ? "positive" : ""}>{detail}</small></div>;
}

function Sidebar({page,setPage}:{page:Page;setPage:(p:Page)=>void}) {
  const [uploadStatus,setUploadStatus]=useState("");
  const [brokerageSelection,setBrokerageSelection]=useState<string[]>([]);
  async function upload(endpoint:string,file:File){
    setUploadStatus("Enviando "+file.name+"…");
    try{
      const form=new FormData();
      form.append("file",file);
      const r=await fetch(API_BASE+endpoint,{method:"POST",body:form});
      const d=await r.json();
      if(!r.ok) throw new Error(d.detail??d.error??"Falha no upload");
      setUploadStatus(d.message??"Arquivo carregado com sucesso");
    }catch(err){
      setUploadStatus("Erro: "+(err instanceof Error?err.message:"falha no upload"));
    }
  }
  async function uploadBrokerageNotes(files:File[]){
    if(!files.length)return;
    setUploadStatus(`Enviando ${files.length} nota(s) de corretagem…`);
    let processed=0;
    let inserted=0;
    try{
      for(const file of files){
        const form=new FormData();
        form.append("file",file);
        const r=await fetch(API_BASE+"/imports/brokerage-notes",{method:"POST",body:form});
        const d=await r.json();
        if(!r.ok) throw new Error(d.detail??d.error??(`Falha ao processar ${file.name}`));
        processed++;
        inserted+=Number(d.inserted_count??0);
      }
      setUploadStatus(`✓ ${processed} nota(s) processada(s) · ${inserted} nova(s) transação(ões) no ledger`);
      setBrokerageSelection(files.map(file=>file.name));
    }catch(err){
      setUploadStatus(`Erro após ${processed}/${files.length} nota(s): ${err instanceof Error?err.message:"falha no processamento"}`);
    }
  }
  return <aside className="sidebar">
    <div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Seu copiloto de investimentos com IA</small></div></div>
    <nav>{nav.map(n=><button key={n.id} className={"nav-item "+(page===n.id?"active":"")} onClick={()=>setPage(n.id)}><span className="nav-icon">{n.icon}</span><span><strong>{n.id}</strong><small>{n.subtitle}</small></span></button>)}</nav>
    <section className="connections"><label>DADOS & CONEXÕES</label>
      <div className="connection"><b>BTG Portfolio</b><span className="status">● Orchestrator</span><small>Snapshot via workflow</small></div>
      <div className="connection"><b>Options Transactions</b><span className="status">● Orchestrator</span><small>Ledger via workflow</small></div>
      <div className="connection"><b>Reconciliação</b><span className="status">● Disponível</span><small>Engine no backend</small></div>
      <label className="load">↥ &nbsp; Carregar planilha BTG<input type="file" accept=".xlsx,.xlsm" hidden onChange={e=>{const file=e.target.files?.[0];if(file)void upload("/imports/portfolio",file);e.currentTarget.value="";}} /></label>
      <label className="load">↥ &nbsp; Carregar transações de opções<input type="file" accept=".xlsx,.xlsm" hidden onChange={e=>{const file=e.target.files?.[0];if(file)void upload("/imports/options",file);e.currentTarget.value="";}} /></label>
      <label className="load">↥ &nbsp; Carregar notas de corretagem<input type="file" accept=".pdf" multiple hidden onChange={e=>{const files=Array.from(e.target.files??[]);if(files.length)void uploadBrokerageNotes(files);e.currentTarget.value="";}} /></label>
      {uploadStatus&&<small className="upload-status" role="status">{uploadStatus}</small>}{brokerageSelection.length>0&&<small className="upload-status" role="status">Notas armazenadas: {brokerageSelection.join(", ")}</small>}
    </section>
    <section className="knowledge-status"><label>BASE DE CONHECIMENTO</label><span>◈ Obsidian <i>Backend</i></span><span>◉ RAG <i>Backend</i></span><span>● Knowledge Graph <i>Backend</i></span></section>
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

type GoldenCase = { id:string; title:string; family:string; question:string; purpose:string };
const GOLDEN_CASES: GoldenCase[] = [
  {id:"GC-C01",title:"Opportunity Discovery",family:"Capital",question:"Tenho R$ 80 mil disponíveis. Existe alguma boa oportunidade?",purpose:"Cruza o capital informado com o OpportunitySet determinístico e o contexto da carteira."},
  {id:"GC-C02",title:"Capital Insufficient",family:"Capital",question:"Tenho R$ 20 mil. Essa PUT cabe na minha carteira?",purpose:"Verifica o requisito de capital e o contexto de carteira antes da análise."},
  {id:"GC-C03",title:"Diversification",family:"Portfolio",question:"Tenho essa carteira. Existe alguma oportunidade que melhore minha diversificação?",purpose:"Considera exposição existente e oportunidades determinísticas."},
  {id:"GC-C04",title:"Position vs Opportunity",family:"Portfolio",question:"Vale a pena analisar uma nova oportunidade em vez de manter essa posição?",purpose:"Compara posição existente, oportunidade relativa e custo de oportunidade quando disponíveis."},
  {id:"GC-C05",title:"BUY vs SELL PUT",family:"Comparison",question:"É melhor comprar PETR4 ou vender uma PUT de PETR4?",purpose:"Compara caminhos determinísticos preservando evidência e contexto da carteira."},
  {id:"GC-C06",title:"Valuation",family:"Valuation",question:"PETR4 está barata?",purpose:"Explica o valuation determinístico disponível sem recalcular valuation no LLM."},
  {id:"GC-C07",title:"Existing PUT",family:"Options",question:"Como está minha PUT e existe alguma alternativa que eu deveria analisar?",purpose:"Combina posição, lifecycle de opções e oportunidades disponíveis sem execução."},
  {id:"GC-C08",title:"Insufficient Evidence",family:"Governance",question:"Qual a melhor coisa para eu fazer agora?",purpose:"Quando faltarem evidências, explicita o que é conhecido e o que precisa de análise adicional."},
];

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
    fetch(API_BASE+"/orchestrate",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        task:"Carregar snapshot do portfolio para o Dashboard",
        context:{client:"react-dashboard",dashboard_view:"portfolio"}
      })
    })
      .then(async r=>{const d=await r.json(); if(!r.ok) throw new Error(d.detail??d.error??"Falha ao consultar o orquestrador"); return d;})
      .then(d=>{
        const snapshot=d.result?.dashboard_snapshot;
        const portfolio=snapshot?.portfolio_context;
        if(!portfolio) throw new Error("Orquestrador não retornou portfolio_context");
        setData({
          status:d.status==="COMPLETED"?"OK":d.status,
          as_of:portfolio.as_of,
          quality_status:portfolio.quality_status,
          cash:portfolio.cash,
          summary:{
            total_value:(portfolio.positions??[]).reduce((sum:number,p:any)=>sum+(p.market_value??0),0)+(portfolio.cash??0),
            stock_value:(portfolio.positions??[]).filter((p:any)=>p.instrument_type==="STOCK").reduce((sum:number,p:any)=>sum+(p.market_value??0),0),
            option_value:(portfolio.positions??[]).filter((p:any)=>p.instrument_type==="OPTION").reduce((sum:number,p:any)=>sum+(p.market_value??0),0),
            position_count:(portfolio.positions??[]).length
          },
          positions:portfolio.positions??[]
        });
        setError("");
      })
      .catch(err=>setError(err instanceof Error?err.message:"Falha ao consultar o orquestrador"))
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
  async function refresh(){ setStatus("Consultando opções via orquestrador…"); try {
    const r=await fetch(API_BASE+"/orchestrate",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        task:"Carregar snapshot das transações de opções para o Dashboard",
        context:{client:"react-dashboard",dashboard_view:"options"}
      })
    });
    const d=await r.json();
    if(!r.ok) throw new Error(d.detail??d.error??"Falha ao consultar o orquestrador");
    const raw=d.result?.dashboard_snapshot?.options_transactions??[];
    const transactions=raw.map((x:any)=>({
      transaction_id:x.transaction_id,
      option_ticker:x.option_ticker,
      date:x.as_of??null,
      side:x.side??"",
      quantity:x.quantity??0,
      execution_price:x.execution_price??null,
      total_amount:x.total_amount??null,
      source_type:x.source_type??"",
      source_id:x.source_id??null,
      note_number:x.note_number??null
    }));
    const performance=d.result?.dashboard_snapshot?.options_performance??{lifecycles:[],by_underlying:[]};
    const lifecycles=performance.lifecycles??[];
    const realized=lifecycles.reduce((sum:any,x:any)=>sum+(x.realized_pnl??0),0);
    const received=lifecycles.reduce((sum:any,x:any)=>sum+(x.premium_received??0),0);
    const paid=lifecycles.reduce((sum:any,x:any)=>sum+(x.premium_paid??0),0);
    const profitable=lifecycles.filter((x:any)=>(x.realized_pnl??0)>0).length;
    const losing=lifecycles.filter((x:any)=>(x.realized_pnl??0)<0).length;
    setData({
      summary:{
        realized_pnl:realized,
        premium_received:received,
        premium_paid:paid,
        return_pct:null,
        lifecycle_count:lifecycles.length,
        profitable_lifecycles:profitable,
        losing_lifecycles:losing
      },
      lifecycles,
      transactions,
      data_quality:{status:"DETERMINISTIC_VIA_ORCHESTRATOR",transactions_included:transactions.length,note:"Lifecycle e P&L calculados pelo OptionPerformanceEngine no backend."}
    });
    setStatus("Dados reais carregados via orquestrador");
  } catch(err) { setStatus("Erro: "+(err instanceof Error?err.message:"falha")); setData(null); } }
  const s=data?.summary;
  const optionTypeByTicker=new Map((data?.lifecycles??[]).map((x:any)=>[x.option_ticker,x.option_type]));
  return <main className="workspace options-page">
    <div className="workspace-head"><div><h1>Options Intelligence</h1><p>Resultado acumulado, rolagens e drill-down por papel.</p></div><span className="updated">{status}</span></div>
    <section className="filters"><label>Ativo<select value={underlying} onChange={e=>setUnderlying(e.target.value)}><option>Todos</option><option>PETR4</option><option>VALE3</option><option>ITUB4</option></select></label><label>Tipo<select value={type} onChange={e=>setType(e.target.value)}><option>Todas</option><option>CALL</option><option>PUT</option></select></label><label>Início<input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>Fim<input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label><button className="primary-btn" onClick={refresh}>Atualizar análise</button></section>
    <section className="cards"><Metric title="P&L realizado acumulado" value={s?money(s.realized_pnl):"—"} detail={s?s.lifecycle_count+" lifecycles confirmados":"Sem consulta"} icon="Σ"/><Metric title="Prêmios recebidos" value={s?money(s.premium_received):"—"} detail={s?s.profitable_lifecycles+" positivos · "+s.losing_lifecycles+" negativos":"Sem consulta"} icon="↓"/><Metric title="Lifecycles" value={s?String(s.lifecycle_count):"—"} detail={data?.data_quality?.transactions_included?data.data_quality.transactions_included+" transações":"Sem consulta"} icon="↻"/><Metric title="Resultado %" value={s?.return_pct!=null?pct(s.return_pct):"—"} detail="Sobre a base de capital disponível" icon="%"/></section>
    <section className="grid-two"><Card title="P&L acumulado"><div className="analytics-summary"><strong>{s?money(s.realized_pnl):"—"}</strong><span>resultado realizado no período selecionado</span><small>{data?.data_quality?.warning??"Os dados são provenientes do ledger persistido."}</small></div></Card><Card title="Qualidade dos dados"><div className="analytics-summary"><strong>{data?.data_quality?.transactions_included??"—"}</strong><span>transações incluídas</span><small>{data?.data_quality?.status??"Ainda não consultado"}</small></div></Card></section>
    <Card title={(underlying==="Todos"?"Todos os ativos":underlying)+" — Lifecycles"}><div className="table-wrap"><table><thead><tr><th>Contrato</th><th>Tipo</th><th>Início</th><th>Fim</th><th>Status</th><th>Operações</th><th>P&L</th><th>Histórico</th></tr></thead><tbody>{(data?.lifecycles??[]).map(x=><tr key={x.option_ticker}><td><strong>{x.option_ticker}</strong></td><td>{x.option_type??"—"}</td><td>{x.first_trade_date??"—"}</td><td>{x.last_trade_date??"—"}</td><td>{x.status}</td><td>{x.transaction_count}</td><td className={(x.realized_pnl??0)>=0?"positive":"negative"}>{x.realized_pnl==null?"—":money(x.realized_pnl)}</td><td>{x.history_completeness}</td></tr>)}{!data?.lifecycles?.length&&<tr><td colSpan={8} className="table-empty">Nenhum lifecycle retornado para os filtros atuais.</td></tr>}</tbody></table></div></Card>
    <Card title="Drill-down — transações individuais"><div className="table-wrap"><table><thead><tr><th>Data</th><th>Contrato</th><th>Tipo</th><th>Lado</th><th>Qtd</th><th>Preço</th><th>Fluxo</th><th>Origem</th></tr></thead><tbody>{(data?.transactions??[]).map(x=><tr key={x.transaction_id}><td>{x.date??"—"}</td><td><strong>{x.option_ticker}</strong></td><td>{optionTypeByTicker.get(x.option_ticker)??"—"}</td><td className={x.side==="SELL"?"positive":"negative"}>{x.side}</td><td>{x.quantity}</td><td>{x.execution_price==null?"—":x.execution_price.toFixed(2)}</td><td>{x.total_amount==null?"—":money(x.total_amount)}</td><td>{x.source_type}{x.note_number?" · Nota "+x.note_number:""}</td></tr>)}{!data?.transactions?.length&&<tr><td colSpan={8} className="table-empty">Nenhuma transação retornada.</td></tr>}</tbody></table></div></Card>
  </main>
}



function Reconciliation(){
  type Match={status:string;excel_transaction_id?:string|null;brokerage_transaction_id?:string|null;reason:string};
  type Coverage={option_ticker:string;first_trade_date?:string|null;last_trade_date?:string|null;transaction_count:number;net_historical_quantity:number;current_position_quantity?:number|null;position_alignment:string;completeness:string};
  type SourceCoverage={source_ref:string;coverage_start?:string|null;coverage_end?:string|null;scope:string;completeness:string};
  type ReconciliationData={quality_status:string;matches:Match[];history_coverage:Coverage[];source_coverage:SourceCoverage[];quantity_mismatches:Array<[string,number,number]>;potential_cross_source_duplicates:Array<[string,string]>};
  const [data,setData]=useState<ReconciliationData|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState("");
  async function refresh(){
    setLoading(true);setError("");
    try{
      const r=await fetch(API_BASE+"/orchestrate",{method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({task:"Carregar reconciliação de opções para o Dashboard",context:{client:"react-dashboard",dashboard_view:"reconciliation"}})});
      const d=await r.json();
      if(!r.ok)throw new Error(d.detail??d.error??"Falha ao consultar o orquestrador");
      const value=d.result?.dashboard_snapshot?.options_reconciliation;
      if(!value)throw new Error("Orquestrador não retornou options_reconciliation");
      setData(value);
    }catch(err){setError(err instanceof Error?err.message:"Falha ao consultar o orquestrador");}
    finally{setLoading(false);}
  }
  useEffect(()=>{void refresh();},[]);
  const matches=data?.matches??[];
  const count=(status:string)=>matches.filter(x=>x.status===status).length;
  return <main className="workspace reconciliation-page">
    <div className="workspace-head"><div><h1>Reconciliação</h1><p>Confronto auditável entre transações do Excel e notas de corretagem, sem alterar o P&L.</p></div><span className="updated">{loading?"Consultando…":data?"Dados reais via Orchestrator":"Sem dados"}</span></div>
    {error&&<div className="analytics-summary copilot-error"><strong>Reconciliação indisponível</strong><span>{error}</span></div>}
    {data&&<section className="cards">
      <Metric title="Qualidade" value={data.quality_status} detail="Status do engine de reconciliação" icon="✓"/>
      <Metric title="Reconciliadas" value={String(count("RECONCILED"))} detail="Excel ↔ Nota" icon="⇄"/>
      <Metric title="Possíveis duplicidades" value={String(count("POTENTIAL_DUPLICATE"))} detail="Requer revisão" icon="!"/>
      <Metric title="Somente uma fonte" value={String(count("EXCEL_ONLY")+count("BROKERAGE_ONLY"))} detail={count("EXCEL_ONLY")+" Excel · "+count("BROKERAGE_ONLY")+" Nota"} icon="◇"/>
    </section>}
    <Card title="Status das transações">
      <div className="table-wrap"><table><thead><tr><th>Status</th><th>Excel</th><th>Nota</th><th>Motivo</th></tr></thead>
      <tbody>{matches.map((x,i)=><tr key={x.excel_transaction_id+"-"+x.brokerage_transaction_id+"-"+i}><td><strong className={x.status==="RECONCILED"?"positive":x.status==="POTENTIAL_DUPLICATE"?"warning-text":""}>{x.status}</strong></td><td>{x.excel_transaction_id??"—"}</td><td>{x.brokerage_transaction_id??"—"}</td><td>{x.reason}</td></tr>)}{!matches.length&&<tr><td colSpan={4} className="table-empty">Nenhum relacionamento retornado.</td></tr>}</tbody></table></div>
    </Card>
    <section className="grid-two">
      <Card title="Cobertura histórica"><div className="table-wrap"><table><thead><tr><th>Contrato</th><th>Transações</th><th>Qtd. líquida</th><th>Posição atual</th><th>Alinhamento</th><th>Completude</th></tr></thead><tbody>{(data?.history_coverage??[]).map(x=><tr key={x.option_ticker}><td><strong>{x.option_ticker}</strong></td><td>{x.transaction_count}</td><td>{x.net_historical_quantity}</td><td>{x.current_position_quantity??"—"}</td><td>{x.position_alignment}</td><td>{x.completeness}</td></tr>)}{!data?.history_coverage?.length&&<tr><td colSpan={6} className="table-empty">Sem cobertura histórica.</td></tr>}</tbody></table></div></Card>
      <Card title="Fontes"><div className="table-wrap"><table><thead><tr><th>Origem</th><th>Período</th><th>Escopo</th><th>Completude</th></tr></thead><tbody>{(data?.source_coverage??[]).map(x=><tr key={x.source_ref}><td>{x.source_ref}</td><td>{x.coverage_start??"—"} → {x.coverage_end??"—"}</td><td>{x.scope}</td><td>{x.completeness}</td></tr>)}{!data?.source_coverage?.length&&<tr><td colSpan={4} className="table-empty">Nenhuma cobertura de fonte registrada.</td></tr>}</tbody></table></div></Card>
    </section>
    {(data?.quantity_mismatches?.length||data?.potential_cross_source_duplicates?.length)&&<Card title="Itens que exigem revisão">
      <div className="analytics-summary"><strong>WARNING</strong><span>{data.quantity_mismatches.length} divergência(s) de quantidade · {data.potential_cross_source_duplicates.length} possível(is) duplicidade(s)</span><small>O engine não faz merge automático desses casos.</small></div>
    </Card>}
  </main>;
}

function PortfolioIntelligence(){
  const [data,setData]=useState<any>(null);
  const [error,setError]=useState("");
  useEffect(()=>{
    fetch(API_BASE+"/orchestrate",{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({task:"Carregar Portfolio Intelligence determinístico",context:{client:"react-dashboard",dashboard_view:"portfolio-intelligence"}})
    }).then(async r=>{const d=await r.json(); if(!r.ok) throw new Error(d.detail??d.error??"Falha ao consultar o orquestrador"); return d;})
      .then(d=>setData(d.result?.dashboard_snapshot?.portfolio_intelligence??null))
      .catch(e=>setError(e instanceof Error?e.message:"Falha ao consultar o orquestrador"));
  },[]);
  const risk=data?.capital_risk;
  return <main className="workspace">
    <div className="workspace-head"><div><h1>Portfolio Intelligence</h1><p>Exposição, cobertura e risco de capital calculados pelos engines determinísticos.</p></div><span className="updated">{data?"Dados reais via Orchestrator":"Carregando…"}</span></div>
    {error&&<div className="analytics-summary"><strong>Erro</strong><span>{error}</span></div>}
    {risk&&<section className="cards">
      <Metric title="Capital para assignment" value={money(risk.assignment_capital)} detail="Short puts" icon="⌂"/>
      <Metric title="Cash após assignment" value={money(risk.cash_after_assignment)} detail={risk.fully_cash_secured?"Cobertura suficiente":"Necessita atenção"} icon="◉"/>
      <Metric title="Calls descobertas" value={String(risk.uncovered_call_shares)} detail="Ações equivalentes" icon="△"/>
      <Metric title="Exposições" value={String(data?.exposures?.length??0)} detail="Por underlying" icon="◇"/>
    </section>}
    <Card title="Exposição por ativo"><div className="table-wrap"><table><thead><tr><th>Underlying</th><th>Valor líquido</th><th>Peso</th><th>Opções</th><th>Short</th><th>Assignment</th><th>Cobertura Call</th></tr></thead><tbody>{(data?.exposures??[]).map((x:any)=><tr key={x.ticker}><td><strong>{x.ticker}</strong></td><td>{money(x.net_market_value??0)}</td><td>{((x.weight??0)*100).toFixed(1).replace(".",",")}%</td><td>{x.option_count}</td><td>{x.short_option_count}</td><td>{money(x.assignment_capital??0)}</td><td>{x.call_coverage_ratio==null?"—":x.call_coverage_ratio.toFixed(2)}</td></tr>)}{!data&& !error&&<tr><td colSpan={7} className="table-empty">Carregando…</td></tr>}{data&&!data.exposures?.length&&<tr><td colSpan={7} className="table-empty">Nenhuma exposição retornada.</td></tr>}</tbody></table></div></Card>
  </main>;
}

function CopilotPage(){
  const [question,setQuestion]=useState("");
  const [selected,setSelected]=useState("GC-C01");
  const [loading,setLoading]=useState(false);
  const [response,setResponse]=useState<any>(null);
  const [error,setError]=useState("");
  const selectedCase=GOLDEN_CASES.find(x=>x.id===selected)??GOLDEN_CASES[0];

  async function ask(nextQuestion=question){
    const q=nextQuestion.trim();
    if(!q||loading)return;
    setQuestion(q); setLoading(true); setError("");
    try{
      const r=await fetch(API_BASE+"/orchestrate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task:q,context:{client:"react-dashboard-copilot",surface:"copilot",use_case_id:selectedCase.id}})});
      const d=await r.json();
      if(!r.ok)throw new Error(d.detail??d.error??"Falha ao consultar o orquestrador");
      setResponse(d);
    }catch(err){setResponse(null);setError(err instanceof Error?err.message:"Falha ao consultar o orquestrador");}
    finally{setLoading(false);}
  }

  const result=response?.result??{};
  const synthesis=result.synthesis??{};
  const proposal=result.decision_proposal??result.proposal??{};
  const risk=result.risk_validation??{};
  const deterministic=result.deterministic_context??{};
  const opportunitySet=deterministic.opportunity_set??{};
  const opportunities=opportunitySet.ranked_opportunities??[];
  const evidence=result.evidence??[];
  const sources=response?.sources??[];
  const asOf=proposal.as_of??opportunitySet.as_of??result.as_of??result.portfolio_context?.as_of??null;
  const quality=result.portfolio_context?.quality_status??opportunitySet.quality_status??"Não informado";

  return <main className="workspace copilot-page">
    <div className="workspace-head"><div><h1>Conversational Investment Copilot</h1><p>Entrada conversacional para o mesmo B3 Orchestrator e LangGraph usados pelo Dashboard.</p></div><span className="updated">{loading?"Consultando Orchestrator…":response?"Resposta estruturada recebida":"Pronto"}</span></div>
    <section className="copilot-contract"><strong>Contrato</strong><span>Pergunta → OrchestratorRequest → contexto determinístico → especialistas → síntese → proposta → Risk Validation → resposta.</span><small>Sem execução de ordens. A decisão final permanece humana.</small></section>
    <div className="copilot-layout">
      <section className="copilot-main">
        <Card title="Golden Conversational Cases"><div className="golden-grid">{GOLDEN_CASES.map(item=><button key={item.id} className={"golden-card "+(selected===item.id?"selected":"")} onClick={()=>{setSelected(item.id);setQuestion(item.question);}}><span>{item.id} · {item.family}</span><strong>{item.title}</strong><small>{item.question}</small></button>)}</div></Card>
        <Card title="Pergunta ao Orchestrator">
          <div className="copilot-question"><textarea aria-label="Pergunta ao Orchestrator" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Ex.: Tenho R$ 80 mil disponíveis. Existe alguma boa oportunidade?" rows={4}/><div><button className="primary-btn" disabled={loading||!question.trim()} onClick={()=>void ask()}>{loading?"Consultando…":"Enviar ao Orchestrator"}</button><span>{selectedCase.purpose}</span></div></div>
        </Card>
        {error&&<div className="analytics-summary copilot-error"><strong>Orchestrator indisponível</strong><span>{error}</span></div>}
        {response&&<>
          <Card title="Resposta / Decision Support"><div className="copilot-answer"><div><label>Questão entendida</label><p>{question}</p></div><div><label>Síntese</label><p>{synthesis.summary??"O workflow retornou uma resposta estruturada, mas não forneceu síntese textual."}</p></div><div><label>Proposta de decisão</label><p>{proposal.thesis??"Não há proposta suficiente para exibir."}</p><small>{proposal.rationale??""}</small></div><div><label>Incertezas</label><ul>{(synthesis.uncertainties??[]).map((x:string)=><li key={x}>{x}</li>)}{!(synthesis.uncertainties??[]).length&&<li>Nenhuma incerteza adicional retornada.</li>}</ul></div></div></Card>
          <section className="cards copilot-metrics">
            <Metric title="Risk Validation" value={risk.status??"N/D"} detail={(risk.reasons??[]).join(" · ")||"Resultado do validador downstream"} icon="✓"/>
            <Metric title="Oportunidades" value={String(opportunities.length)} detail={opportunitySet.ranking_policy_version?"Ranking determinístico":"Nenhum OpportunitySet disponível"} icon="✦"/>
            <Metric title="Data quality" value={String(quality)} detail={asOf?"as_of "+String(asOf):"as_of não informado"} icon="◉"/>
            <Metric title="Human review" value="REQUIRED" detail="Copilot não executa ordens" icon="⌁"/>
          </section>
          <Card title="Proveniência e auditoria"><div className="provenance-grid"><div><label>Sources</label><p>{sources.length?sources.join(" · "):"Nenhuma fonte explícita retornada."}</p></div><div><label>Evidence</label><p>{evidence.length?String(evidence.length)+" evidências recuperadas":"Nenhuma evidência recuperada."}</p></div><div><label>Decision proposal</label><p>{proposal.action??"N/D"}{proposal.subject_id?" · "+proposal.subject_id:""}</p></div><div><label>Risk reasons</label><p>{(risk.reasons??[]).join(" · ")||"Nenhum motivo adicional."}</p></div></div><details><summary>Ver resposta estruturada completa</summary><pre className="answer">{JSON.stringify(response,null,2)}</pre></details></Card>
        </>}
      </section>
      <aside className="copilot-sidebar"><Card title="Regras do Copilot"><ul><li>Não cria oportunidades.</li><li>Não altera ranking determinístico.</li><li>Não recalcula valuation silenciosamente.</li><li>Não ignora restrições da carteira.</li><li>Não executa ordens.</li><li>Se faltar evidência, declara a lacuna.</li></ul></Card><Card title="Arquitetura"><div className="journey"><div className="journey-step"><b>1</b><span>Contexto</span></div><div className="journey-line"/><div className="journey-step"><b>2</b><span>Agents</span></div><div className="journey-line"/><div className="journey-step"><b>3</b><span>Risk</span></div></div></Card></aside>
    </div>
  </main>;
}

function Card({title,action,children}:{title:string;action?:ReactNode;children:ReactNode}){return <div className="panel"><div className="panel-title"><h2>{title}</h2>{action}</div>{children}</div>}

function App(){const [page,setPage]=useState<Page>("Portfolio"); return <div className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Seu copiloto de investimentos com IA</small></div></div><div className="search">⌕ <span>Buscar ativos, estratégias ou fazer uma pergunta...</span><kbd>Ctrl K</kbd></div><div className="market"><span>Mercado <b>via Orchestrator</b></span><span className="bell">♧</span><span className="avatar">EF</span><b>Edmilson⌄</b></div></header><div className="body"><Sidebar page={page} setPage={setPage}/><div>{page==="Portfolio"?<Portfolio/>:page==="Options"?<Options/>:page==="Reconciliation"?<Reconciliation/>:page==="Portfolio Intelligence"?<PortfolioIntelligence/>:page==="Copilot"?<CopilotPage/>:<main className="workspace"><div className="workspace-head"><div><h1>{page}</h1><p>Workspace React preparado para o próximo módulo.</p></div></div><div className="panel placeholder"><h2>{page}</h2><p>Este módulo será conectado aos engines Python existentes sem duplicar a lógica de negócio.</p></div></main>}</div><Copilot setPage={setPage}/></div></div>}

export default App;
