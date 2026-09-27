import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError, b3Api } from "./api/client";
import type { OrchestrateResponse } from "./api/contracts";
import {
  PAGE_DEFINITIONS,
  getPageDefinition,
  hashForPage,
  pageFromHash,
  type PageId,
} from "./app/pages";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "erro desconhecido";
}

function App() {
  const [page, setPage] = useState<PageId>(() => pageFromHash());
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<OrchestrateResponse | null>(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [asking, setAsking] = useState(false);
  const [importStatus, setImportStatus] = useState("");

  useEffect(() => {
    const syncPageFromHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", syncPageFromHash);
    if (!window.location.hash) {
      window.history.replaceState(null, "", hashForPage("Overview"));
    }
    return () => window.removeEventListener("hashchange", syncPageFromHash);
  }, []);

  useEffect(() => {
    let active = true;
    b3Api
      .health()
      .then((health) => {
        if (active) setServerOnline(health.status === "ok");
      })
      .catch(() => {
        if (active) setServerOnline(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const pageDefinition = useMemo(() => getPageDefinition(page), [page]);

  function navigate(nextPage: PageId) {
    window.location.hash = hashForPage(nextPage);
    setPage(nextPage);
    setAnswer(null);
  }

  async function ask(event?: FormEvent) {
    event?.preventDefault();
    const task = (question.trim() || pageDefinition.prompt).trim();
    if (!task || asking) return;

    setAsking(true);
    setAnswer(null);
    try {
      const response = await b3Api.orchestrate({
        task,
        context: {
          client: "react-production-v1",
          dashboard_page: page,
        },
      });
      setAnswer(response);
      setServerOnline(true);
    } catch (error) {
      setAnswer({
        status: "ERROR",
        result: {},
        sources: [],
        audit: [],
        error: errorMessage(error),
      });
      setServerOnline(false);
    } finally {
      setAsking(false);
    }
  }

  async function importExcel(
    event: ChangeEvent<HTMLInputElement>,
    kind: "portfolio" | "options",
  ) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    setImportStatus(
      `Validando e carregando ${kind === "portfolio" ? "portfolio de ações" : "transações de opções"}…`,
    );

    try {
      const data =
        kind === "portfolio"
          ? await b3Api.importPortfolio(file)
          : await b3Api.importOptions(file);
      setImportStatus(
        `✓ ${data.file} carregado. Snapshot atual substituído após validação.`,
      );
      setServerOnline(true);
    } catch (error) {
      setImportStatus(`Erro: ${errorMessage(error)}`);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">▮▮▮</span>
          <div>
            <strong>B3 Investment Copilot</strong>
            <small>Production React · Architecture V4 frozen</small>
          </div>
        </div>
        <div className="architecture-badge">
          SQLite/Parquet · Qdrant 768d hybrid · Neo4j
        </div>
        <div className="user">EF&nbsp;&nbsp;Edmilson</div>
      </header>

      <div className="body">
        <aside className="sidebar">
          <nav>
            {PAGE_DEFINITIONS.map((item) => (
              <button
                key={item.id}
                className={page === item.id ? "nav-item active" : "nav-item"}
                onClick={() => navigate(item.id)}
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
              <input
                type="file"
                accept=".xlsx,.xlsm"
                hidden
                onChange={(event) => importExcel(event, "portfolio")}
              />
            </label>

            <div className="connection">
              <b>Operações / Opções</b>
              <span className="status">● Import validado</span>
            </div>
            <label className="load secondary">
              ↥ &nbsp; Carregar Excel de Opções
              <input
                type="file"
                accept=".xlsx,.xlsm"
                hidden
                onChange={(event) => importExcel(event, "options")}
              />
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
              <p>{pageDefinition.description}</p>
            </div>
            <span className={serverOnline ? "server online" : "server"}>
              ● Backend {serverOnline ? "Connected" : "Offline"}
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
              <h2>Runtime contratado</h2>
              <div className="list-item">PIT / Quality Gates <span>Deterministic</span></div>
              <div className="list-item">Experience Retrieval <span>Hybrid</span></div>
              <div className="list-item">Learning Lifecycle <span>Drift-aware</span></div>
              <div className="list-item">Risk Validation <span>Downstream</span></div>
              <div className="list-item">Order Execution <span>Disabled</span></div>
            </div>
          </section>

          <section className="panel lower">
            <h2>Frontend contract</h2>
            <p>
              O React consome apenas APIs existentes do backend congelado. Ausência,
              UNKNOWN, LIMITED, qualidade, evidências e timestamps permanecem explícitos;
              nenhuma métrica de investimento é recalculada ou inferida no navegador.
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
            <p>{pageDefinition.prompt}</p>
          </div>

          <div className="suggestions">
            <button onClick={() => setQuestion(pageDefinition.prompt)}>
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
              placeholder={pageDefinition.prompt}
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

function PageSurface({
  page,
  answer,
}: {
  page: PageId;
  answer: OrchestrateResponse | null;
}) {
  const features: Record<PageId, string[]> = {
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
        <pre className="result-json">{JSON.stringify(answer.result, null, 2)}</pre>
      ) : (
        <div className="empty-state">
          <div className="empty-icon">◇</div>
          <h3>Nenhum resultado canônico carregado</h3>
          <p>
            Use “Atualizar inteligência” ou o Copilot. A interface não cria métricas
            substitutas quando o runtime não fornece dados.
          </p>
        </div>
      )}
    </div>
  );
}

function AnswerCard({ payload }: { payload: OrchestrateResponse }) {
  return (
    <div className="answer-card">
      <div className="answer-status">{payload.status || "UNKNOWN"}</div>
      {payload.error ? (
        <p>{payload.error}</p>
      ) : (
        <pre>{JSON.stringify(payload.result, null, 2)}</pre>
      )}
      {!!payload.sources.length && <small>Sources: {payload.sources.join(", ")}</small>}
    </div>
  );
}

function Metric({
  title,
  value,
  detail,
}: {
  title: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="metric">
      <span>{title}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

export default App;
