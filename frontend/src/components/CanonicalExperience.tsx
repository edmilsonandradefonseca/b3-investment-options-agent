type Obj = Record<string, unknown>;
const object = (value: unknown): Obj | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Obj : null;
const rows = (value: unknown): Obj[] => Array.isArray(value) ? value.map(object).filter((item): item is Obj => item !== null) : [];
const text = (value: unknown) => typeof value === 'string' ? value : 'Indisponível';
const numeric = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? String(value) : 'Indisponível';
const strings = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string').join(', ') || 'Indisponível' : 'Indisponível';

export default function CanonicalExperience({ value }: { value: unknown }) {
  const context = object(value);
  if (!context) return null;
  const assessment = object(context.assessment);
  const learnings = rows(context.learnings);
  const status = text(context.status);
  const unavailable = status === 'CANONICAL_LOADER_NOT_CONFIGURED' || status === 'TYPED_SNAPSHOT_AND_REGIME_REQUIRED';
  return <section className="analysis-section">
    <h4>Experience / Learning canônicos</h4>
    {unavailable ? <p className="muted">{status === 'CANONICAL_LOADER_NOT_CONFIGURED' ? 'Leitura canônica de Experience/Learning ainda não configurada.' : 'Snapshot e regime tipados são necessários para consultar precedentes.'} As execuções observadas permanecem separadas; nenhum learning é admitido por texto da conversa.</p> : <>
      <p>Similaridade: {numeric(assessment?.historical_similarity)} · Confiança: {numeric(assessment?.confidence)}</p>
      <p>Learnings favoráveis: {strings(assessment?.supporting_learning_ids)} · Contrários: {strings(assessment?.contradicting_learning_ids)}</p>
      {!learnings.length && <p className="muted">Nenhum learning elegível neste corte. Isso não comprova uma tese nem ausência de perdas.</p>}
      {learnings.length > 0 && <div className="table-wrap"><table><thead><tr><th>Learning</th><th>Estado</th><th>Amostra</th><th>Confiança</th><th>Escopo</th><th>Atualizado em</th></tr></thead><tbody>{learnings.map(item => <tr key={text(item.learning_id)}><td>{text(item.learning_id)}</td><td>{text(item.status)}</td><td>{numeric(item.sample_size)}</td><td>{numeric(item.confidence)}</td><td>{text(item.learning_scope)}</td><td>{text(item.last_updated_at)}</td></tr>)}</tbody></table></div>}
      {learnings.map(item => <details key={text(item.learning_id)}><summary>{text(item.learning_id)} — evidências e validade</summary>
        <p>{text(item.statement)}</p>
        <p className="muted">Condições: {strings(item.conditions)} · Regimes: {strings(item.regime_ids)}</p>
        <p className="muted">Válido desde: {text(item.valid_from)} · Até: {text(item.valid_to)} · Modelo: {text(item.model_version)} · Schema: {text(item.schema_version)}</p>
        <p className="muted">População: {text(item.population_scope)} · {text(item.selection_bias_warning)}</p>
        <ul>{rows(item.evidence_links).map((link, index) => <li key={index}>{text(link.direction)}: {text(link.evidence_id)} · operação {text(link.operation_id)} · fonte {text(link.source_ref)} · observado em {text(link.observed_at)}</li>)}</ul>
        {typeof item.evidence_details_omitted === 'number' && item.evidence_details_omitted > 0 && <p className="muted">Evidências adicionais omitidas: {item.evidence_details_omitted}.</p>}
        <p className="muted">Proveniência: {text(item.provenance)} · Fontes: {strings(item.source_refs)}</p>
        {typeof item.source_details_omitted === 'number' && item.source_details_omitted > 0 && <p className="muted">Fontes adicionais omitidas: {item.source_details_omitted}.</p>}
      </details>)}
      {typeof context.learning_details_omitted === 'number' && context.learning_details_omitted > 0 && <p className="muted">Learnings adicionais omitidos: {context.learning_details_omitted}.</p>}
      {Array.isArray(assessment?.limitations) && <ul>{assessment.limitations.map((item, index) => <li key={index}>{text(item)}</li>)}</ul>}
    </>}
    <p className="muted">Amostras pessoais não estimam probabilidade de exercício no mercado. A consulta não altera o ranking determinístico.</p>
  </section>;
}
