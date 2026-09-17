import { FormEvent, useEffect, useState } from "react";

type Page = "Portfolio" | "Options" | "Opportunities" | "Portfolio Intelligence" | "Knowledge";

const API_BASE = import.meta.env.VITE_ORCHESTRATOR_URL ?? "http://127.0.0.1:8000";

const nav: { id: Page; icon: string; subtitle: string }[] = [
  { id: "Portfolio", icon: "◫", subtitle: "Posições e visão geral" },
  { id: "Options", icon: "◈", subtitle: "Greeks, risco e operações" },
  { id: "Opportunities", icon: "◎", subtitle: "Ideias e sinais" },
  { id: "Portfolio Intelligence", icon: "◇", subtitle: "Análises e recomendações" },
  { id: "Knowledge", icon: "▱", subtitle: "Pesquisa e contexto" },
];

function App() {
  const [page, setPage] = useState<Page>("Portfolio");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [serverOnline, setServerOnline] = useState(false);
  const [asking, setAsking] = useState(false);
  const [showTransaction, setShowTransaction] = useState(false);
  const [transactionStatus, setTransactionStatus] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((response) => setServerOnline(response.ok))
      .catch(() => setServerOnline(false));
  }, []);

  async function ask(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || asking) return;
    setAsking(true);
    setAnswer("");
    try {
      const response = await fetch(`${API_BASE}/orchestrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: question.trim(), context: { client: "desktop" } }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? data.error ?? "Falha no orquestrador");
      setAnswer(data.result?.answer ?? data.result?.summary ?? JSON.stringify(data.result, null, 2));
    } catch (error) {
      setAnswer(`Orquestrador indisponível: ${error instanceof Error ? error.message : "erro desconhecido"}`);
    } finally {
      setAsking(false);
    }
  }


  async function addTransaction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setTransactionStatus("");
    try {
      const response = await fetch(`${API_BASE}/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: form.get("action"),
          instrument_type: form.get("instrument_type"),
          ticker: String(form.get("ticker") ?? "").toUpperCase(),
          quantity: Number(form.get("quantity")),
          price: Number(form.get("price")),
          executed_at: new Date(String(form.get("executed_at"))).toISOString(),
          broker: form.get("broker"),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Falha ao registrar operação");
      setTransactionStatus(`✓ ${data.action} ${data.quantity} ${data.ticker} registrada`);
      event.currentTarget.reset();
    } catch (error) {
      setTransactionStatus(`Erro: ${error instanceof Error ? error.message : "falha desconhecida"}`);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">▮▮▮</span><div><strong>B3 Investment Copilot</strong><small>Seu copiloto de investimentos com IA</small></div></div>
        <div className="search">⌕&nbsp; Buscar ativos, estratégias, ou fazer uma pergunta...</div>
        <div className="market"><span>IBOV <b>—</b></span><span>DÓLAR <b>—</b></span><span>PETR4 <b>—</b></span></div>
        <div className="user">EF&nbsp;&nbsp;Edmilson⌄</div>
      </header>

      <div className="body">
        <aside className="sidebar">
          <nav>
            {nav.map((item) => (
              <button key={item.id} className={page === item.id ? "nav-item active" : "nav-item"} onClick={() => setPage(item.id)}>
                <span className="nav-icon">{item.icon}</span><span><strong>{item.id}</strong><small>{item.subtitle}</small></span>
              </button>
            ))}
          </nav>
          <section className="connections">
            <label>DADOS &amp; CONEXÕES</label>
            <div className="connection"><b>BTG Portfolio</b><span className="status">● Aguardando</span></div>
            <div className="connection"><b>Options Transactions</b><span className="status">● Aguardando</span></div>
            <button className="load" onClick={() => setShowTransaction(true)}>＋ &nbsp; Registrar operação</button><button className="load secondary">↥ &nbsp; Carregar Arquivos Excel</button>
          </section>
          <section className="knowledge-status">
            <label>BASE DE CONHECIMENTO</label>
            <span>◈ Obsidian <i>Não conectado</i></span>
            <span>◉ RAG (Qdrant) <i>Infra pronta</i></span>
            <span>● Neo4j <i>Infra pronta</i></span>
          </section>
        </aside>

        <main className="workspace">
          <div className="workspace-head"><div><h1>Olá, Edmilson! 👋</h1><p>{page} · interface desktop V0.1</p></div><span className={serverOnline ? "server online" : "server"}>● Orchestrator {serverOnline ? "Connected" : "Offline"}</span></div>

          <section className="cards">
            <Metric title="Valor Total" value="Aguardando dados" />
            <Metric title="Cash" value="Aguardando dados" />
            <Metric title="Ações" value="Aguardando dados" />
            <Metric title="Opções" value="Aguardando dados" />
          </section>

          <section className="main-grid">
            <div className="panel hero-panel">
              <div className="panel-title"><h2>{page}</h2><span>Dados reais serão carregados na próxima etapa</span></div>
              <div className="empty-state">
                <div className="empty-icon">{page === "Opportunities" ? "◎" : page === "Portfolio Intelligence" ? "◇" : "▦"}</div>
                <h3>Workspace preparado</h3>
                <p>A estrutura visual está pronta. Não exibimos números ou recomendações fictícias.</p>
              </div>
            </div>
            <div className="panel insights"><h2>Próximos dados</h2><div className="list-item">Portfolio BTG <span>Excel</span></div><div className="list-item">Options Transactions <span>Excel</span></div><div className="list-item">Market / News <span>Orchestrator</span></div><div className="list-item">Knowledge <span>RAG + KG</span></div></div>
          </section>

          <section className="panel lower"><h2>Inteligência</h2><p>Esta área será alimentada pelos engines determinísticos, OpportunitySet e agentes especializados. O dashboard não calcula nem inventa recomendações.</p></section>
        </main>

        <aside className="copilot">
          <div className="copilot-head"><div><strong>AI Copilot</strong><small>Seu time de agentes especialistas</small></div><span className={serverOnline ? "online-dot" : "offline-dot"}>● {serverOnline ? "Online" : "Offline"}</span></div>
          <div className="agent-tabs"><button className="selected">Chat</button><button>Agentes</button><button>Histórico</button></div>
          <div className="copilot-intro"><h2>Olá, Edmilson! 👋</h2><p>Faça perguntas sobre seu portfólio, opções, oportunidades e contexto de mercado.</p></div>
          <div className="suggestions">
            {["Quais são as oportunidades disponíveis?", "Como está o risco da minha carteira?", "Analise minhas opções atuais", "Quais eventos podem afetar minhas posições?"] .map((q) => <button key={q} onClick={() => setQuestion(q)}>{q}<span>›</span></button>)}
          </div>
          {answer && <pre className="answer">{answer}</pre>}
          <form onSubmit={ask} className="chat-form"><select defaultValue="general"><option value="general">Investment Copilot (Geral)</option><option value="options">Options Agent</option><option value="market">Market Agent</option><option value="risk">Risk Agent</option></select><textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Digite sua pergunta aqui..." rows={4} /><button disabled={asking}>{asking ? "Enviando..." : "➤"}</button></form>
          <small className="disclaimer">Sem execução de ordens. O orquestrador permanece responsável pela inteligência.</small>
        </aside>
      </div>
    </div>
  );
}

function Metric({ title, value }: { title: string; value: string }) {
  return <div className="metric"><span>{title}</span><strong>{value}</strong><small>Sem dados carregados</small></div>;
}

export default App;
