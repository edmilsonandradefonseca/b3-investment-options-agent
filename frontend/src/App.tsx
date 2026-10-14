import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import { ApiError, b3Api, getApiBaseUrl, setApiBaseUrl } from "./api/client";
import type { OrchestrateResponse } from "./api/contracts";
import {
  PAGE_DEFINITIONS,
  getPageDefinition,
  hashForPage,
  pageFromHash,
  type PageId,
  type PageTab,
} from "./app/pages";
import { ResultSurface } from "./components/ResultSurface";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "erro desconhecido";
}

function App() {
  const [page, setPage] = useState<PageId>(() => pageFromHash());
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<OrchestrateResponse | null>(null);
  const [serverOnline, setServerOnline] = useState(false);
  const [asking, setAsking] = useState(false);
  const [importStatus, setImportStatus] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [backendUrl, setBackendUrl] = useState(() => getApiBaseUrl());

  useEffect(() => {
    const syncPageFromHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", syncPageFromHash);
    if (!window.location.hash) window.history.replaceState(null, "", hashForPage("Overview"));
    return () => window.removeEventListener("hashchange", syncPageFromHash);
  }, []);

  const pageDefinition = useMemo(() => getPageDefinition(page), [page]);
  const selectedTab: PageTab | null = useMemo(() => {
    const tabs = pageDefinition.tabs ?? [];
    return tabs.find((tab) => tab.id === activeTab) ?? tabs[0] ?? null;
  }, [pageDefinition, activeTab]);

  const prompt = selectedTab?.prompt ?? pageDefinition.prompt;
  const description = selectedTab?.description ?? pageDefinition.description;
  const useCases = selectedTab?.useCases ?? pageDefinition.useCases;

  async function checkBackend() {
    try {
      const health = await b3Api.health();
      setServerOnline(health.status === "ok");
      return true;
    } catch {
      setServerOnline(false);
      return false;
    }
  }

  useEffect(() => {
    checkBackend();
  }, []);

  function navigate(nextPage: PageId) {
    window.location.hash = hashForPage(nextPage);
    setPage(nextPage);
    setActiveTab(null);
    setAnswer(null);
    setQuestion("");
  }

  async function runAnalysis(task = prompt) {
    if (!task.trim() || asking) return;
    setAsking(true);
    setAnswer(null);
    try {
      const response = await b3Api.orchestrate({
        task: task.trim(),
        context: {
          client: "windows-react-production-v1",
          dashboard_page: page,
          dashboard_tab: selectedTab?.id ?? null,
          use_cases: useCases,
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
      // An HTTP error proves the backend is reachable. Only transport/fetch
      // failures should mark the backend itself offline.
      setServerOnline(error instanceof ApiError);
    } finally {
      setAsking(false);
    }
  }

  async function ask(event?: FormEvent) {
    event?.preventDefault();
    await runAnalysis(question.trim() || prompt);
  }

  async function importExcel(
    event: ChangeEvent<HTMLInputElement>,
    kind: "portfolio" | "options",
  ) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setImportStatus(`Loading ${kind === "portfolio" ? "portfolio" : "options"} snapshot…`);
    try {
      const data = kind === "portfolio"
        ? await b3Api.importPortfolio(file)
        : await b3Api.importOptions(file);
      setImportStatus(`✓ ${data.file} validated and activated.`);
      setServerOnline(true);
    } catch (error) {
      setImportStatus(`Error: ${errorMessage(error)}`);
    }
  }

  async function saveBackend(event: FormEvent) {
    event.preventDefault();
    try {
      const normalized = setApiBaseUrl(backendUrl);
      setBackendUrl(normalized);
      const ok = await checkBackend();
      if (ok) setSettingsOpen(false);
    } catch (error) {
      setImportStatus(`Backend URL: ${errorMessage(error)}`);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">▮▮▮</span>
          <div>
            <strong>B3 Investment Copilot</strong>
            <small>Windows 11 · React + Tauri · V4 frozen</small>
          </div>
        </div>
        <div className="architecture-badge">SQLite/Parquet · Qdrant 768d hybrid · Neo4j</div>
        <button className="backend-button" onClick={() => setSettingsOpen(true)}>
          <span className={serverOnline ? "online-dot" : "offline-dot"}>●</span>
          {serverOnline ? "Backend online" : "Configure backend"}
        </button>
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
            <label>REAL DATA</label>
            <label className="load">
              ↥ &nbsp; BTG Portfolio Excel
              <input type="file" accept=".xlsx,.xlsm" hidden onChange={(event) => importExcel(event, "portfolio")} />
            </label>
            <label className="load secondary">
              ↥ &nbsp; Options Excel
              <input type="file" accept=".xlsx,.xlsm" hidden onChange={(event) => importExcel(event, "options")} />
            </label>
            {importStatus && <small className="import-status">{importStatus}</small>}
          </section>

          <section className="knowledge-status">
            <label>RUNTIME</label>
            <span>▦ Structured <i>SQLite / Parquet</i></span>
            <span>◉ Semantic <i>Qdrant hybrid</i></span>
            <span>● Relational <i>Neo4j</i></span>
          </section>
        </aside>

        <main className="workspace">
          <div className="workspace-head">
            <div>
              <div className="uc-row">{useCases.map((uc) => <span key={uc}>{uc}</span>)}</div>
              <h1>{page}</h1>
              <p>{description}</p>
            </div>
            <button className="refresh" onClick={() => runAnalysis()} disabled={asking}>
              {asking ? "Loading real runtime…" : "Refresh"}
            </button>
          </div>

          {!!pageDefinition.tabs?.length && (
            <div className="workspace-tabs">
              {pageDefinition.tabs.map((tab) => (
                <button
                  key={tab.id}
                  className={selectedTab?.id === tab.id ? "selected" : ""}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setAnswer(null);
                    setQuestion("");
                  }}
                >
                  {tab.label}
                  <small>{tab.useCases.join(" · ")}</small>
                </button>
              ))}
            </div>
          )}

          <section className="cards">
            <Metric title="Authority" value="Backend" detail="No calculations in React" />
            <Metric title="Freshness" value="as_of" detail="Always preserved when supplied" />
            <Metric title="Data gaps" value="Explicit" detail="UNKNOWN / LIMITED visible" />
            <Metric title="Execution" value="Disabled" detail="Decision support only" />
          </section>

          <section className="panel production-panel">
            <div className="panel-title">
              <div>
                <h2>Canonical intelligence</h2>
                <span>{useCases.join(" · ")}</span>
              </div>
              <span className={serverOnline ? "server online" : "server"}>
                ● {serverOnline ? getApiBaseUrl() : "backend offline"}
              </span>
            </div>
            <ResultSurface response={answer} />
          </section>
        </main>

        <aside className="copilot">
          <div className="copilot-head">
            <div>
              <strong>Copilot</strong>
              <small>Same frozen backend, contextual query</small>
            </div>
            <span className={serverOnline ? "online-dot" : "offline-dot"}>●</span>
          </div>

          <div className="copilot-intro">
            <h2>{selectedTab?.label ?? page}</h2>
            <p>{prompt}</p>
          </div>

          <div className="suggestions">
            <button onClick={() => setQuestion(prompt)}>Use workspace query <span>›</span></button>
            <button onClick={() => setQuestion("O que mudou desde a última análise? Preserve as_of e fontes.")}>What changed? <span>›</span></button>
            <button onClick={() => setQuestion("Quais dados estão LIMITED, UNKNOWN ou ausentes e como isso limita a análise?")}>Data limitations <span>›</span></button>
          </div>

          {answer?.error && <div className="answer-card"><p>{answer.error}</p></div>}

          <form onSubmit={ask} className="chat-form">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask about this workspace…"
              rows={5}
            />
            <button disabled={asking}>{asking ? "…" : "➤"}</button>
          </form>

          <small className="disclaimer">No order execution. Human remains final decision authority.</small>
        </aside>
      </div>

      {settingsOpen && (
        <div className="modal-backdrop" onClick={() => setSettingsOpen(false)}>
          <div className="transaction-modal" onClick={(event) => event.stopPropagation()}>
            <div className="panel-title">
              <div>
                <h2>Backend connection</h2>
                <span>Windows app → real B3 backend instance</span>
              </div>
              <button onClick={() => setSettingsOpen(false)}>×</button>
            </div>
            <form className="transaction-form" onSubmit={saveBackend}>
              <label>Backend URL</label>
              <input
                value={backendUrl}
                onChange={(event) => setBackendUrl(event.target.value)}
                placeholder="http://ubuntu:8000"
                autoFocus
              />
              <button type="submit">Save and test connection</button>
            </form>
          </div>
        </div>
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
