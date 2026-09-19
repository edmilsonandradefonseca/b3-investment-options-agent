import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

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

function money(v:number){ return new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL",maximumFractionDigits:0}).format(v); }

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
  const [range,setRange]=useState("1M");
  const points=useMemo(()=>history.map((v,i)=>({v,i})),[]);
  const min=Math.min(...history),max=Math.max(...history);
  const poly=points.map(p=>((p.i/(points.length-1))*100).toFixed(1)+","+((max-p.v)/(max-min)*80+10).toFixed(1)).join(" ");
  return <main className="workspace"><div className="workspace-head"><div><h1>Olá, Edmilson! 👋</h1><p>Aqui está a visão geral da sua carteira.</p></div><span className="updated">◷ Atualizado em 18/09/2026 10:24 &nbsp; ↻</span></div>
    <section className="cards">
      <Metric title="Valor Total" value={money(352480)} detail="▲ +2,34% (+R$ 8.054)" icon="↗"/>
      <Metric title="Cash" value={money(42360)} detail="12,0% da carteira" icon="◉"/>
      <Metric title="Ações" value={money(289120)} detail="82,0% da carteira" icon="▥"/>
      <Metric title="Opções (Valor Líquido)" value={money(21000)} detail="6,0% da carteira" icon="◈"/>
    </section>
    <section className="grid-two">
      <Card title="Evolução da Carteira" action={<div className="range">{["1M","3M","6M","YTD","ALL"].map(x=><button key={x} className={range===x?"on":""} onClick={()=>setRange(x)}>{x}</button>)}</div>}>
        <div className="line-chart"><div className="y-labels"><span>380K</span><span>360K</span><span>340K</span><span>320K</span><span>300K</span></div><svg viewBox="0 0 600 230" preserveAspectRatio="none"><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1684ff" stopOpacity=".28"/><stop offset="1" stopColor="#1684ff" stopOpacity="0"/></linearGradient></defs><path d={"M 0 205 L "+poly.replace(/,/g," ").replace(/ /g," L ").replace(/(\d+\.\d+) (\d+\.\d+)/g,"$1 $2")} fill="none" stroke="#1684ff" strokeWidth="3"/></svg></div>
        <div className="chart-caption"><span>18 Ago</span><span>25 Ago</span><span>01 Set</span><span>08 Set</span><span>15 Set</span><b>+3,31%</b></div>
      </Card>
      <Card title="Alocação de Ativos"><div className="allocation"><div className="donut"><div className="donut-hole"><b>R$ 352.480</b><span>carteira</span></div></div><div className="legend">{allocation.map(a=><div key={a.label}><i style={{background:a.color}}/><span>{a.label}</span><b>{a.value.toFixed(1).replace(".",",")}%</b></div>)}</div></div></Card>
    </section>
    <section className="grid-two">
      <Card title="Top Posições"><table><thead><tr><th>Ativo</th><th>Qtd</th><th>Preço Médio</th><th>Atual</th><th>Valor (R$)</th><th>P&L</th><th>P&L %</th></tr></thead><tbody>{positions.map(p=><tr key={p.ticker}><td><strong>{p.ticker}</strong></td><td>{p.qty}</td><td>{p.avg.toFixed(2)}</td><td>{p.price.toFixed(2)}</td><td>{p.value.toLocaleString("pt-BR")}</td><td className="positive">+{p.pnl.toLocaleString("pt-BR")}</td><td className="positive">+{p.pct.toFixed(1)}%</td></tr>)}</tbody></table></Card>
      <Card title="P&L por Categoria"><div className="pnl-list">{[["Ações",8450],["Opções",2890],["Dividendos",420],["Taxas",-475]].map(([n,v])=><div className="pnl-row" key={String(n)}><span>{n}</span><div className="bar-track"><div className={Number(v)>=0?"bar gain":"bar loss"} style={{width:Math.max(8,Math.abs(Number(v))/8450*100)+"%"}}/></div><strong className={Number(v)>=0?"positive":"negative"}>{Number(v)>=0?"+":""}{money(Number(v))}</strong></div>)}</div></Card>
    </section>
    <section className="grid-two">
      <Card title="Principais Insights"><div className="insights">{["PETR4: acompanhar resultado acumulado das covered calls.","VALE3: P&L positivo no histórico carregado.","Revisar concentração financeira e exposição a opções.","Explorar rolagens para entender o resultado por estratégia."].map(x=><div key={x}>● <span>{x}</span></div>)}</div></Card>
      <Card title="Acesso rápido"><div className="quick"><button>Explorar opções de PETR4 <span>›</span></button><button>Ver resultado acumulado por papel <span>›</span></button><button>Abrir Analytics Lab <span>›</span></button></div></Card>
    </section>
  </main>;
}

function Card({title,action,children}:{title:string;action?:React.ReactNode;children:React.ReactNode}){return <div className="panel"><div className="panel-title"><h2>{title}</h2>{action}</div>{children}</div>}

function App(){const [page,setPage]=useState<Page>("Portfolio"); return <div className="app-shell"><header className="topbar"><div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Seu copiloto de investimentos com IA</small></div></div><div className="search">⌕ <span>Buscar ativos, estratégias ou fazer uma pergunta...</span><kbd>Ctrl K</kbd></div><div className="market"><span>IBOV <b>134.521</b> <i>+1,2%</i></span><span>DÓLAR <b>4,92</b> <em>-0,3%</em></span><span>PETR4 <b>37,20</b> <i>+2,1%</i></span><span className="bell">♧</span><span className="avatar">EF</span><b>Edmilson⌄</b></div></header><div className="body"><Sidebar page={page} setPage={setPage}/><div>{page==="Portfolio"?<Portfolio/>:<main className="workspace"><div className="workspace-head"><div><h1>{page}</h1><p>Workspace React preparado para o próximo módulo.</p></div></div><div className="panel placeholder"><h2>{page}</h2><p>O shell React já está pronto. Este módulo será conectado aos engines Python existentes sem duplicar a lógica de negócio.</p></div></main>}</div><Copilot setPage={setPage}/></div></div>}

export default App;
