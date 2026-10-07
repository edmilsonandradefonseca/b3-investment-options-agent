import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { b3Api, getApiBaseUrl } from "../api/client";
import type { CollectionUniverseResponse, RuntimeStatusResponse } from "../api/contracts";
import { State } from "./cockpit";

const labels: Record<string, string> = {
  embedding: "Embeddings",
  qdrant: "Qdrant",
  neo4j: "Neo4j",
  openclaw_gateway: "OpenClaw Gateway",
};
const stateLabel = (value: unknown) => {
  if (value === "ok" || value === "running") return "Operacional";
  if (value === "unavailable" || value === "failed" || value === "stopped" || value === "missing") return "Indisponível";
  return typeof value === "string" && value ? value : "Não informado";
};
const portFrom = (endpoint?: string) => {
  if (!endpoint) return "—";
  try { return new URL(endpoint).port || (endpoint.startsWith("https:") ? "443" : "80"); }
  catch { return "—"; }
};

export default function AdminWorkspace() {
  const [status, setStatus] = useState<RuntimeStatusResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [universe, setUniverse] = useState<CollectionUniverseResponse | null>(null);
  const [universeDraft, setUniverseDraft] = useState<string[]>([]);
  const [tickerDraft, setTickerDraft] = useState("");
  const [savingUniverse, setSavingUniverse] = useState(false);
  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [runtimeResult, universeResult] = await Promise.allSettled([
        b3Api.runtimeStatus(),
        b3Api.collectionUniverse(),
      ]);
      if (runtimeResult.status === "fulfilled") setStatus(runtimeResult.value);
      if (universeResult.status === "fulfilled") {
        setUniverse(universeResult.value);
        setUniverseDraft(universeResult.value.configured_tickers);
      }
      const failures = [runtimeResult, universeResult]
        .filter((result): result is PromiseRejectedResult => result.status === "rejected")
        .map(result => result.reason instanceof Error ? result.reason.message : String(result.reason));
      if (failures.length) setError(failures.join(" · "));
    } finally {
      setLoading(false);
    }
  }, []);

  async function saveUniverse() {
    setSavingUniverse(true);
    setError("");
    try {
      const result = await b3Api.saveCollectionUniverse(universeDraft);
      setUniverse(result);
      setUniverseDraft(result.configured_tickers);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingUniverse(false);
    }
  }

  function addTickers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const candidates = tickerDraft.split(/[,;\s]+/).filter(Boolean).map(value => value.toUpperCase());
    const invalid = candidates.filter(value => !/^[A-Z]{4}\d{1,2}$/.test(value));
    if (invalid.length) {
      setError(`Ticker inválido: ${invalid.join(", ")}. Use símbolos B3, por exemplo PETR4.`);
      return;
    }
    setError("");
    setUniverseDraft(current => Array.from(new Set([...current, ...candidates])));
    setTickerDraft("");
  }

  useEffect(() => { void refresh(); }, [refresh]);

  const services = Object.entries(status?.services ?? {});
  const resources = Object.entries(status?.resources ?? {});
  const endpoint = status?.api?.local_health_url || getApiBaseUrl() + "/health";

  return <div className="admin-workspace">
    <section className="panel">
      <div className="panel-heading">
        <div><h2>Conexão com o backbone</h2><p className="muted">O aplicativo desktop usa este endereço para falar com o runtime B3.</p></div>
        <button className="secondary" onClick={refresh} disabled={loading}>{loading ? "Atualizando…" : "Atualizar status"}</button>
      </div>
      <div className="cards">
        <div className="metric"><span>API do orquestrador</span><strong>{stateLabel(status?.health)}</strong><small>{endpoint}</small></div>
        <div className="metric"><span>Host configurado</span><strong>{status?.api?.host ?? "—"}</strong><small>Porta {status?.api?.port ?? portFrom(getApiBaseUrl())}</small></div>
        <div className="metric"><span>Processo</span><strong>{status?.process?.running ? "Em execução" : stateLabel(status?.runtime)}</strong><small>{status?.process?.orchestrator_pid ? `PID ${status.process.orchestrator_pid}` : "PID não informado"}</small></div>
      </div>
      <p className="muted">Endereço configurado no desktop: <strong>{getApiBaseUrl()}</strong>. Para alterá-lo, use “Configurar servidor Ubuntu” no menu lateral.</p>
    </section>

    <section className="panel">
      <h2>Serviços internos</h2>
      <p className="muted">Portas e estados lidos do endpoint operacional do backend.</p>
      {services.length ? <div className="table-wrap"><table><thead><tr><th>Serviço</th><th>Estado</th><th>Host</th><th>Porta</th></tr></thead><tbody>
        {services.map(([key, item]) => {
          const service = item as { state?: string; endpoint?: string; ownership?: string };
          let host = "—"; try { host = service.endpoint ? new URL(service.endpoint).hostname : "—"; } catch {}
          return <tr key={key}><td>{labels[key] ?? key}</td><td>{stateLabel(service.state)}</td><td>{host}</td><td>{portFrom(service.endpoint)}</td></tr>;
        })}
      </tbody></table></div> : <State kind={status ? "limited" : "loading"} title={status ? "Serviços não informados" : "Consultando serviços"}>{status ? "O backend conectado não retornou a lista de serviços." : "Lendo o estado operacional do runtime."}</State>}
      {resources.length > 0 && <p className="muted">Recursos locais: {resources.map(([name, value]) => `${name}: ${stateLabel(value)}`).join(" · ")}</p>}
    </section>

    <section className="panel">
      <h2>Ações monitoradas pelo scheduler</h2>
      <p className="muted">As ações da carteira são incluídas automaticamente. Esta lista adicional alimenta as próximas coletas CVM, notícias e histórico.</p>
      <form className="inline-controls" onSubmit={addTickers}>
        <label>Adicionar tickers B3<input value={tickerDraft} onChange={event => setTickerDraft(event.target.value)} placeholder="VALE3, ITUB4" aria-label="Adicionar tickers B3"/></label>
        <button type="submit" disabled={!tickerDraft.trim()}>Adicionar</button>
      </form>
      {universeDraft.length ? <div className="ticker-list">{universeDraft.map(ticker => <span className="badge" key={ticker}>{ticker}<button className="ghost" type="button" aria-label={`Remover ${ticker}`} onClick={() => setUniverseDraft(current => current.filter(value => value !== ticker))}>×</button></span>)}</div> : <State title="Nenhum ativo adicional configurado">Os ativos da carteira continuam incluídos nas coletas.</State>}
      <div className="section-head"><small className="muted">Fonte: {universe?.source ?? "não carregada"}{universe?.updated_at ? ` · Atualizado em ${universe.updated_at}` : ""}</small><button onClick={saveUniverse} disabled={savingUniverse || !universe}>{savingUniverse ? "Salvando…" : "Salvar universo"}</button></div>
      <small className="muted">A mudança vale nas próximas execuções; não interrompe uma coleta em andamento. Universo efetivo: {universe?.effective_tickers.join(", ") || "sem tickers"}</small>
    </section>

    <section className="panel">
      <h2>Agendamentos e OpenClaw</h2>
      {status?.scheduler?.state === "ok" && status.scheduler.timers.length > 0 ? <div className="table-wrap"><table><thead><tr><th>Timer</th><th>Próxima execução</th><th>Última execução</th><th>Serviço</th></tr></thead><tbody>
        {status.scheduler.timers.map(timer => <tr key={timer.unit}><td>{timer.unit}</td><td>{timer.next ?? "Não agendada"}</td><td>{timer.last ?? "Sem execução registrada"}</td><td>{timer.activates ?? "—"}</td></tr>)}
      </tbody></table></div> : <State kind={status?.scheduler?.state === "ok" ? "limited" : "loading"} title={status?.scheduler?.state === "ok" ? "Nenhum timer B3 encontrado" : "Status do scheduler indisponível"}>{status?.scheduler?.state === "ok" ? "O systemd não retornou timers com prefixo b3-." : "A API ainda não conseguiu consultar os timers do systemd."}</State>}
      {!status?.services?.openclaw_gateway && <State kind="limited" title="OpenClaw não reportado">A API conectada não retornou status do Gateway.</State>}
      <div className="state-banner limited"><strong>Edição dos agendamentos ainda não disponível.</strong><span>Os horários e ativos monitorados ainda são definidos nos serviços systemd e nos jobs. A tela exibe os disparos reais, mas não altera o scheduler.</span></div>
    </section>
    {error && <div className="state-banner error" role="alert"><strong>Não foi possível carregar o status</strong><span>{error}</span></div>}
  </div>;
}
