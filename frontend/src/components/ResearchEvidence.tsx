type Obj = Record<string, unknown>;
const obj = (v: unknown): Obj => v && typeof v === 'object' && !Array.isArray(v) ? v as Obj : {};
const arr = (v: unknown): Obj[] => Array.isArray(v) ? v.map(obj) : [];
const text = (v: unknown) => typeof v === 'string' ? v : 'Indisponível';
const date = (v: unknown) => typeof v === 'string' && !Number.isNaN(Date.parse(v)) ? new Date(v).toLocaleString('pt-BR') : 'Indisponível';
export default function ResearchEvidence({ stored, market }: { stored: unknown; market: unknown }) {
  const entries = Object.entries(obj(stored));
  if (!entries.length) return null;
  const tickers = obj(obj(market).tickers);
  return <section className="analysis-section"><h4>Notícias e eventos usados na análise</h4>
    <p className="muted">Evidência de research com fontes e datas. A consulta não garante cobertura completa de eventos.</p>
    {entries.map(([ticker, value]) => {
      const memory = obj(value), current = obj(tickers[ticker]), acquisition = obj(current.research_acquisition);
      const events = arr(current.research_events ?? (ticker === 'IBOV' ? obj(market).market_overview_research : memory.events));
      return <details key={ticker}><summary>{ticker} · {events.length} evidências · {acquisition.external_search_requested === true ? 'busca complementar solicitada' : 'base existente'}</summary>
        {!events.length && <p className="muted">Sem research recente admissível neste corte. Eventos desconhecidos permanecem desconhecidos.</p>}
        {events.map((event, index) => <article key={`${text(event.source_ref)}-${index}`}>
          <strong>{text(event.headline)}</strong><p>{typeof event.summary === 'string' ? event.summary : ''}</p>
          <p className="muted">Publicado: {date(event.published_at)} · Disponível: {date(event.available_at)} · Origem: {Array.isArray(event.retrieved_from) ? event.retrieved_from.map(text).join(', ') : 'provedor de research'}</p>
          {typeof event.source_ref === 'string' && /^https?:\/\//.test(event.source_ref) ? <a href={event.source_ref} target="_blank" rel="noreferrer">{event.source_ref}</a> : <span>{text(event.source_ref)}</span>}
        </article>)}
        <details><summary>Disponibilidade das bases e exclusões</summary><p>Qdrant: {text(obj(memory.backends).qdrant)} · Neo4j: {text(obj(memory.backends).neo4j)}</p>
          {Object.entries(obj(memory.excluded)).map(([reason, count]) => <p key={reason}>{reason}: {String(count)}</p>)}
          {arr(memory.relations).map((relation, index) => <p key={index}>{text(relation.source_id)} → {text(relation.relation)} → {text(relation.target_id)} · {text(relation.source_ref)}</p>)}
        </details>
      </details>;
    })}
  </section>;
}
