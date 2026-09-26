import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

type Page =
  | "Overview"
  | "Portfolio"
  | "Options"
  | "Opportunities"
  | "Market Regime"
  | "Experience & Learning"
  | "Historical Similarity"
  | "Risk & Stress"
  | "Copilot";

type OrchestratorPayload = {
  status?: string;
  result?: Record<string, unknown>;
  sources?: string[];
  audit?: Array<Record<string, unknown>>;
  error?: string | null;
};

const API_BASE = import.meta.env.VITE_ORCHESTRATOR_URL ?? "http://127.0.0.1:8000";

const nav: { id: Page; icon: string; subtitle: string }[] = [
  { id: "Overview", icon: "⌂", subtitle: "Visão consolidada V4" },
  { id: "Portfolio", icon: "◫", subtitle: "Posições e exposição" },
  { id: "Options", icon: "◈", subtitle: "Lifecycle e estruturas" },
  { id: "Opportunities", icon: "◎", subtitle: "Ranking + contexto" },
  { id: "Market Regime", icon: "◌", subtitle: "Regime e fatores" },
  { id: "Experience & Learning", icon: "◇", subtitle: "Aprendizados e drift" },
  { id: "Historical Similarity", icon: "≈", subtitle: "Precedentes similares" },
  { id: "Risk & Stress", icon: "△", subtitle: "Cenários e stress" },
  { id: "Copilot", icon: "✦", subtitle: "Racional conversacional" },
];

const pagePrompts: Record<Page, string> = {
  Overview: "Resuma o estado atual do portfólio, mercado, riscos e principais mudanças.",
  Portfolio: "Analise a composição, concentração, capital e exposições do meu portfólio.",
  Options: "Analise minhas posições e operações de opções atuais, incluindo lifecycle e riscos.",
  Opportunities: "Quais oportunidades atuais são elegíveis e como a experiência histórica as contextualiza?",
  "Market Regime": "Qual é o regime de mercado atual e quais fatores o suportam?",
  "Experience & Learning": "Quais aprendizados ativos, enfraquecendo ou em drift são relevantes agora?",
  "Historical Similarity": "Quais experiências históricas são mais similares ao contexto atual e por quê?",
  "Risk & Stress": "Mostre os principais riscos e cenários de stress relevantes para a carteira atual.",
  Copilot: "Explique o racional consolidado para o contexto atual, com evidências e limitações.",
};

const pageDescription: Record<Page, string> = {
  Overview: "Resumo executivo sem inventar dados ausentes.",
  Portfolio: "Fonte: PortfolioContext e engines determinísticos.",
  Options: "Posições, obrigações, assignment e estruturas.",
  Opportunities: "Score determinístico separado de ExperienceAssessment.",
  "Market Regime": "Classificação reproduzível e versionada.",
  "Experience & Learning": "Evidências, confiança, aging, contradição e drift.",
  "Historical Similarity": "Feature similarity + regime + aging + semântica.",
  "Risk & Stress": "ScenarioDefinition → StressResult, sem previsão implícita.",
  Copilot: "Síntese contextual; decisão final continua humana.",
};

function App() {
  const [page, setPage] = useState<Page>("Overview");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<OrchestratorPayload | null>(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [asking, setAsking] = useState(false);
  const [importStatus, setImportStatus] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/health`)
      .then((response) => setServerOnline(response.ok))
      .catch(() => setServerOnline(false));
  }, []);

  const suggestedPrompt = useMemo(() => pagePrompts[page], [page]);

  async function ask(event?: FormEvent) {
    event?.preventDefault();
    const task = (question.trim() || suggestedPrompt).trim();
    if (!task || asking) return;
    setAsking(true);
    setAnswer(null);
    try {
      const response = await fetch(`${API_BASE}/orchestrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task,
          context: {
            client: "desktop-v4",
            dashboard_page: page,
          },
        }),
      });
      const data = (await response.json()) as OrchestratorPayload & { detail?: string };
      if (!response.ok) throw new Error(data.detail ?? data.error ?? "Falha no orquestrador");
      setAnswer(data);
    } catch (error) {
      setAnswer({
        status: "ERROR",
        error: error instanceof Error ? error.message : "erro desconhecido",
      });
    } finally {
      setAsking(false);
    }
  }

  async function importExcel(event: ChangeEvent<HTMLInputElement>, kind: "portfolio" | "options") {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setImportStatus(`Validando e carregando ${kind === "portfolio" ? "portfolio de ações" : "transações de opções"}…`);
    try {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${API_BASE}/imports/${kind}`, {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "Falha ao importar Excel");
      setImportStatus(`✓ ${data.file} carregado. Snapshot atual substituído após validação.`);
    } catch (error) {
      setImportStatus(`Erro: ${error instanceof Error ? error.message : "falha desconhecida"}`);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">▮▮▮</span>
          <div>
            <strong>B3 Investment Copilot</strong>
            <small>Architecture V4 · Continuous Learning</small>
          </div>
        </div>
        <div className="architecture-badge">SQLite/Parquet · Qdrant 768d · Neo4j</div>
        <div className="user">EF&nbsp;&nbsp;Edmilson</div>
      </header>

      <div className="body">
        <aside className="sidebar">
          <nav>
            {nav.map((item) => (
              <button
                key={item.id}
                className={page === item.id ? "nav-item active" : "nav-item"}
                onClick={() => setPage(item.id)}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>
                  <strong>{item.id}</strong>
                  <small>{item.subtitle}</small>
                </span>
              </button>
            ))}
          </nav>

          <section className="connections">
            <label>DADOS</label>
            <div className="connection">
              <b>Portfolio atual</b>
              <span className="status">● Snapshot substitutivo</span>
            </div>
            <label className="load">
              ↥ &nbsp; Carregar Excel de Ações
              <input type="file" accept=".xlsx,.xlsm" hidden onChange={(event) => importExcel(event, "portfolio")} />
            </label>

            <div className="connection">
              <b>Operações / Opções</b>
              <span className="status">● Import validado</span>
            </div>
            <label className="load secondary">
              ↥ &nbsp; Carregar Excel de Opções
              <input type="file" accept=".xlsx,.xlsm" hidden onChange={(event) => importExcel(event, "options")} />
            </label>
            {importStatus && <small className="import-status">{importStatus}</small>}
          </section>

          <section className="knowledge-status">
            <label>MEMÓRIA V4</label>
            <span>▦ Structured <i>SQLite / Parquet</i></span>
            <span>◉ Semantic <i>Qdrant 768d</i></span>
            <span>● Relational <i>Neo4j</i></span>
          </section>
        </aside>

        <main className="workspace">
          <div className="workspace-head">
            <div>
              <h1>{page}</h1>
              <p>{pageDescription[page]}</p>
            </div>
            <span className={serverOnline ? "server online" : "server"}>
              ● Orchestrator {serverOnline ? "Connected" : "Offline"}
            </span>
          </div>

          <section className="cards">
            <Metric title="Current State" value="Canonical only" detail="Sem números fictícios" />
            <Metric title="Market Regime" value="On demand" detail="Versionado e PIT" />
            <Metric title="Experience" value="Hybrid retrieval" detail="Recency ≠ regime" />
            <Metric title="Learning" value="Lifecycle aware" detail="Support + contradiction" />
          </section>

          <section className="main-grid">
            <div className="panel hero-panel">
              <div className="panel-title">
                <h2>{page}</h2>
                <button className="refresh" onClick={() => ask()} disabled={asking}>
                  {asking ? "Consultando…" : "Atualizar inteligência"}
                </button>
              </div>
              <PageSurface page={page} answer={answer} />
            </div>

            <div className="panel insights">
              <h2>Arquitetura ativa</h2>
              <div className="list-item">PIT / Quality Gates <span>Deterministic</span></div>
              <div className="list-item">Experience Retrieval <span>Hybrid</span></div>
              <div className="list-item">Learning Lifecycle <span>Drift-aware</span></div>
              <div className="list-item">Risk Validation <span>Downstream</span></div>
              <div className="list-item">Order Execution <span>Disabled</span></div>
            </div>
          </section>

          <section className="panel lower">
            <h2>What changed</h2>
            <p>
              A V4 usa AnalysisRun + Change Detection para comparar snapshots, regime, learnings,
              oportunidades e riscos. Quando não houver histórico canônico suficiente, o dashboard
              deve mostrar ausência de dados em vez de fabricar uma explicação.
            </p>
          </section>
        </main>

        <aside className="copilot">
          <div className="copilot-head">
            <div>
              <strong>AI Copilot</strong>
              <small>Contexto determinístico + experiência + evidência</small>
            </div>
            <span className={serverOnline ? "online-dot" : "offline-dot"}>
              ● {serverOnline ? "Online" : "Offline"}
            </span>
          </div>

          <div className="copilot-intro">
            <h2>{page}</h2>
            <p>{suggestedPrompt}</p>
          </div>

          <div className="suggestions">
            <button onClick={() => setQuestion(suggestedPrompt)}>
              Usar pergunta sugerida <span>›</span>
            </button>
            <button onClick={() => setQuestion("O que mudou desde a última análise?")}>
              O que mudou? <span>›</span>
            </button>
            <button onClick={() => setQuestion("Quais aprendizados contradizem a análise atual?")}>
              Evidência contraditória <span>›</span>
            </button>
          </div>

          {answer && <AnswerCard payload={answer} />}

          <form onSubmit={ask} className="chat-form">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder={suggestedPrompt}
              rows={5}
            />
            <button disabled={asking}>{asking ? "…" : "➤"}</button>
          </form>

          <small className="disclaimer">
            Sem execução de ordens. Experiência histórica contextualiza; não substitui cálculo determinístico.
          </small>
        </aside>
      </div>
    </div>
  );
}

function PageSurface({ page, answer }: { page: Page; answer: OrchestratorPayload | null }) {
  const features: Record<Page, string[]> = {
    Overview: ["Portfolio", "Market Regime", "Learning", "Risk", "What changed"],
    Portfolio: ["Exposure", "Concentration", "Capital", "Assignment", "Portfolio impact"],
    Options: ["Lifecycle", "DTE", "Assignment", "Coverage", "Historical outcome"],
    Opportunities: ["Deterministic score", "ExperienceAssessment", "Evidence", "Risk"],
    "Market Regime": ["Trend", "Volatility", "Risk appetite", "Rates", "Foreign flow", "Commodity"],
    "Experience & Learning": ["Status", "Confidence", "Recent vs long-term", "Contradictions", "Drift"],
    "Historical Similarity": ["Feature similarity", "Regime similarity", "Temporal score", "Semantic score"],
    "Risk & Stress": ["ScenarioDefinition", "Portfolio P&L", "Assignment capital", "Concentration", "Sensitivities"],
    Copilot: ["Synthesis", "Rationale", "Evidence refs", "Limitations", "Human decision"],
  };

  return (
    <div className="surface">
      <div className="feature-grid">
        {features[page].map((feature) => (
          <div className="feature-card" key={feature}>
            <span>{feature}</span>
            <strong>—</strong>
            <small>Aguardando dado canônico</small>
          </div>
        ))}
      </div>
      {answer ? (
        <pre className="result-json">{JSON.stringify(answer.result ?? {}, null, 2)}</pre>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">◇</div>
          <h3>Nenhum resultado V4 carregado</h3>
          <p>
            Use “Atualizar inteligência” ou o Copilot. A interface não cria métricas substitutas
            quando o runtime não fornece dados canônicos.
          </p>
        </div>
      )}
    </div>
  );
}

function AnswerCard({ payload }: { payload: OrchestratorPayload }) {
  return (
    <div className="answer-card">
      <div className="answer-status">{payload.status ?? "UNKNOWN"}</div>
      {payload.error ? (
        <p>{payload.error}</p>
      ) : (
        <pre>{JSON.stringify(payload.result ?? {}, null, 2)}</pre>
      )}
      {!!payload.sources?.length && (
        <small>Sources: {payload.sources.join(", ")}</small>
      )}
    </div>
  );
}

function Metric({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <div className="metric">
      <span>{title}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export default App;
