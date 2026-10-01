import type { OrchestrateResponse } from '../api/contracts';

type Obj = Record<string, unknown>;

const asObject = (value: unknown): Obj | null =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Obj)
    : null;

const asStrings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];

const asArray = (value: unknown): unknown[] => Array.isArray(value) ? value : [];

const asText = (value: unknown): string | null =>
  typeof value === 'string' && value.trim() ? value.trim() : null;

const numberValue = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;

const brl = (value: number | null) =>
  value == null ? null : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

const pct = (value: number | null) =>
  value == null ? null : new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 2 }).format(value);

function BulletSection({ title, values }: { title: string; values: string[] }) {
  if (!values.length) return null;
  return <section className="analysis-section"><h4>{title}</h4><ul>{values.map((item, index) => <li key={index}>{item}</li>)}</ul></section>;
}

export default function AnalysisOutput({ data }: { data: OrchestrateResponse | null }) {
  if (!data) return <p className="muted">Consulte o backend para obter análise canônica.</p>;

  const result = data.result || {};
  const synthesis = asObject(result.synthesis);
  const proposal =
    asObject(result.proposal) ??
    asObject(result['decision proposal']) ??
    asObject(result.decision_proposal);
  const portfolioContext = asObject(result.portfolio_context);
  const portfolioIntelligence = asObject(result.portfolio_intelligence);
  const capitalRisk = asObject(portfolioIntelligence?.capital_risk);
  const fastRoute = asObject(result.fast_route);
  const strategyComparison = asObject(result.strategy_comparison);
  const assetEvidence = asObject(result.asset_evidence);
  const evidenceEntries = assetEvidence
    ? Object.entries(assetEvidence)
        .map(([key, value]) => [key, asObject(value)] as const)
        .filter((entry): entry is readonly [string, Obj] => entry[1] !== null)
    : [];

  const summary =
    asText(result.summary) ??
    asText(synthesis?.summary) ??
    asText(proposal?.thesis) ??
    asText(asObject(result['market agent analysis'])?.summary) ??
    asText(asObject(result['portfolio agent analysis'])?.summary) ??
    asText(asObject(result['options agent analysis'])?.summary);

  const rationale = asText(proposal?.rationale);
  const agreements = asStrings(synthesis?.agreements);
  const uncertainties = asStrings(synthesis?.uncertainties);
  const evidenceGaps = asStrings(synthesis?.evidence_gaps);
  const risks = asStrings(proposal?.risks);
  const limitations = asStrings(result.limitations);
  const positions = asArray(portfolioContext?.positions);
  const asOf = asText(proposal?.as_of) ?? asText(result.as_of) ?? asText(portfolioContext?.as_of);
  const quality = asText(result.quality_status) ?? asText(portfolioContext?.quality_status);
  const assignmentCapital = numberValue(capitalRisk?.assignment_capital);
  const uncoveredCallShares = numberValue(capitalRisk?.uncovered_call_shares);

  return <div className="output human-output">
    <div className="analysis-status">
      <strong>{data.status}</strong>
      {quality && <span>Qualidade: {quality}</span>}
      {asOf && <span>as_of: {asOf}</span>}
      {asText(fastRoute?.target) && <span>Rota: {asText(fastRoute?.target)}</span>}
    </div>

    {data.error && <div className="state-banner error">{data.error}</div>}

    {summary && <section className="analysis-summary"><h3>Resumo</h3><p>{summary}</p></section>}

    {rationale && <section className="analysis-section"><h4>Racional</h4><p>{rationale}</p></section>}

    {!summary && positions.length > 0 && <section className="analysis-section">
      <h4>Carteira canônica</h4>
      <p>{positions.length} posições no snapshot{asOf ? ` de ${asOf}` : ''}.</p>
      {(assignmentCapital != null || uncoveredCallShares != null) && <p>
        {assignmentCapital != null ? `Capital potencial de exercício/assign: ${brl(assignmentCapital)}.` : ''}
        {uncoveredCallShares != null ? ` Ações descobertas em calls: ${uncoveredCallShares}.` : ''}
      </p>}
    </section>}

    {evidenceEntries.length > 0 && <section className="analysis-section">
      <h4>Fatos determinísticos por ativo</h4>
      <div className="evidence-grid">
        {evidenceEntries.map(([ticker, evidence]) => {
          const market = asObject(evidence.market);
          const latest = asObject(market?.latest);
          const quant = asObject(evidence.quant);
          const fundamentals = asObject(evidence.fundamentals);
          const portfolio = asObject(evidence.portfolio);
          const close = numberValue(latest?.close);
          const volume = numberValue(latest?.volume);
          const vol20 = numberValue(quant?.volatility_20d);
          const vol60 = numberValue(quant?.volatility_60d);
          const drawdown = numberValue(quant?.max_drawdown);
          const rsi = numberValue(quant?.rsi_14);
          const metricCount = numberValue(fundamentals?.metric_count);
          const held = portfolio?.held === true;
          const quantity = numberValue(portfolio?.stock_quantity);
          return <article className="evidence-card" key={ticker}>
            <h5>{ticker}</h5>
            <dl>
              <div><dt>Último preço</dt><dd>{brl(close) ?? 'Indisponível'}</dd></div>
              <div><dt>Volume</dt><dd>{volume == null ? 'Indisponível' : new Intl.NumberFormat('pt-BR').format(volume)}</dd></div>
              <div><dt>Volatilidade 20d</dt><dd>{pct(vol20) ?? 'Indisponível'}</dd></div>
              <div><dt>Volatilidade 60d</dt><dd>{pct(vol60) ?? 'Indisponível'}</dd></div>
              <div><dt>Drawdown histórico</dt><dd>{pct(drawdown) ?? 'Indisponível'}</dd></div>
              <div><dt>RSI 14</dt><dd>{rsi == null ? 'Indisponível' : rsi.toFixed(1)}</dd></div>
              <div><dt>Fundamentos BRAPI</dt><dd>{metricCount == null ? 'Indisponível' : `${metricCount} métricas`}</dd></div>
              <div><dt>Na carteira</dt><dd>{held ? `Sim${quantity != null ? ` · ${quantity} ações` : ''}` : 'Não'}</dd></div>
            </dl>
          </article>;
        })}
      </div>
      {strategyComparison && <p className="muted">
        Comparação canônica disponível. Ranking: {asText(asObject(strategyComparison.assumptions)?.ranking) ?? 'não aplicado'}.
      </p>}
    </section>}

    <BulletSection title="Pontos confirmados" values={agreements} />
    <BulletSection title="Riscos" values={risks} />
    <BulletSection title="Incertezas" values={uncertainties} />
    <BulletSection title="Lacunas de evidência" values={evidenceGaps} />
    <BulletSection title="Limitações" values={limitations} />

    {data.sources?.length > 0 && <details className="analysis-sources">
      <summary>Fontes ({data.sources.length})</summary>
      {data.sources.map((source, index) => <p key={index}>{source}</p>)}
    </details>}

    <details className="technical-output">
      <summary>Detalhes técnicos</summary>
      <pre>{JSON.stringify(result, null, 2)}</pre>
    </details>
  </div>;
}
