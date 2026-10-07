import { useCallback, useEffect, useState } from "react";
import { b3Api, getApiBaseUrl } from "../api/client";
import type { RuntimeStatusResponse } from "../api/contracts";
import { State } from "./cockpit";

const labels: Record<string, string> = {
  embedding: "Embeddings",
  qdrant: "Qdrant",
  neo4j: "Neo4j",
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
  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try { setStatus(await b3Api.runtimeStatus()); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  }, []);
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
      <h2>Agendamentos e OpenClaw</h2>
      <div className="state-banner limited"><strong>Configuração de agendamentos ainda não disponível pela API.</strong><span>O backend atual instala timers systemd com horários definidos nos scripts. A tela ainda não pode editar ativos monitorados, frequência ou horário com efeito no scheduler.</span></div>
      <div className="state-banner limited"><strong>Status do OpenClaw não reportado.</strong><span>A rota operacional atual não expõe o estado do Gateway nem suas portas; esses dados não serão inferidos a partir de outros serviços.</span></div>
    </section>
    {error && <div className="state-banner error" role="alert"><strong>Não foi possível carregar o status</strong><span>{error}</span></div>}
  </div>;
}
