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

const when = (value: unknown) =>
  typeof value === 'string' && value
    ? new Date(value).toLocaleString('pt-BR')
    : 'Indisponível';

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
  const workspaceIntelligence = asObject(result.workspace_intelligence);
  const marketAgent = asObject(result.market_agent_analysis);
  const portfolioAgent = asObject(result.portfolio_agent_analysis);
  const optionsAgent = asObject(result.options_agent_analysis);
  const workspaceMarket = asObject(workspaceIntelligence?.market_context);
  const workspaceDerived = asObject(workspaceIntelligence?.derived_intelligence);
  const joaoPerspective = asObject(workspaceDerived?.joao_resolve);
  const joaoMemory = asObject(workspaceDerived?.joao_memory_context);
  const localIntelligence = asObject(workspaceDerived?.b3_local_evidence_analyst);
  const workspaceMacro = asObject(workspaceMarket?.macro);
  const broadMarketResearch = asArray(workspaceMarket?.market_overview_research);
  const broadMarketDiagnostics = asArray(workspaceMarket?.market_overview_diagnostics);
  const opportunitySet = asObject(result.opportunity_set);
  const rankedOpportunities = asArray(opportunitySet?.ranked_opportunities)
    .map(asObject)
    .filter((item): item is Obj => item !== null);
  const optionMarketability = asObject(result.option_marketability);
  const assetEvidence = asObject(result.asset_evidence);
  const optionEvidence = asObject(result.option_evidence);
  const optionEvidenceEntries = optionEvidence
    ? Object.entries(optionEvidence)
        .map(([key, value]) => [key, asObject(value)] as const)
        .filter((entry): entry is readonly [string, Obj] => entry[1] !== null)
    : [];
  const evidenceEntries = assetEvidence
    ? Object.entries(assetEvidence)
        .map(([key, value]) => [key, asObject(value)] as const)
        .filter((entry): entry is readonly [string, Obj] => entry[1] !== null)
    : [];

  const deterministicSummary = asText(result.summary);
  const seniorSummary =
    asText(synthesis?.summary) ??
    asText(proposal?.thesis) ??
    asText(marketAgent?.summary) ??
    asText(portfolioAgent?.summary) ??
    asText(optionsAgent?.summary) ??
    asText(asObject(result['market agent analysis'])?.summary) ??
    asText(asObject(result['portfolio agent analysis'])?.summary) ??
    asText(asObject(result['options agent analysis'])?.summary);
  const summary = workspaceIntelligence
    ? seniorSummary ?? deterministicSummary
    : deterministicSummary ?? seniorSummary;

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

    {workspaceIntelligence && <section className="analysis-section">
      <h4>Inteligência integrada</h4>
      <p className="muted">
        Fatos numéricos permanecem sob autoridade dos serviços B3. DeepSeek, João Resolve e os agentes senior interpretam as evidências sem substituir esses fatos.
      </p>
      <div className="evidence-grid">
        {marketAgent && <article className="evidence-card">
          <h5>Agente B3 · Mercado</h5>
          <p>{asText(marketAgent.summary) ?? 'Sem síntese disponível.'}</p>
        </article>}
        {portfolioAgent && <article className="evidence-card">
          <h5>Agente B3 · Portfólio</h5>
          <p>{asText(portfolioAgent.summary) ?? 'Sem síntese disponível.'}</p>
        </article>}
        {optionsAgent && <article className="evidence-card">
          <h5>Agente B3 · Opções</h5>
          <p>{asText(optionsAgent.summary) ?? 'Sem síntese disponível.'}</p>
        </article>}
        {joaoPerspective && <article className="evidence-card">
          <h5>João Resolve · Pesquisa</h5>
          <p>{asText(joaoPerspective.summary) ?? (asText(joaoPerspective.status) === 'UNAVAILABLE' ? 'Indisponível nesta execução.' : 'Sem síntese disponível.')}</p>
          <small>Autoridade: inteligência derivada, não canônica.</small>
          {joaoMemory && <p className="muted">
            Memória João: {asText(joaoMemory.status) === 'UNAVAILABLE'
              ? 'serviço indisponível nesta execução'
              : `${asArray(joaoMemory.memories).length} memória(s) · ${asArray(joaoMemory.relations).length} relação(ões)`}
          </p>}
        </article>}
      </div>

      {(workspaceMacro || broadMarketResearch.length > 0) && <div className="analysis-section">
        <h5>Contexto de mercado</h5>
        {workspaceMacro && <p>
          {['SELIC','CDI','IPCA'].map(key => {
            const row = asObject(workspaceMacro[key]);
            const value = numberValue(row?.value);
            return row ? `${key}: ${value == null ? 'indisponível' : value.toLocaleString('pt-BR')} ${String(row.unit ?? '')}` : null;
          }).filter(Boolean).join(' · ')}
        </p>}
        {broadMarketResearch.length > 0 && <p className="muted">
          {broadMarketResearch.length} evidências recentes de mercado amplo disponíveis para a síntese.
        </p>}
      </div>}

      {localIntelligence && <details>
        <summary>DeepSeek local · inteligência B3 por ativo</summary>
        {Object.entries(localIntelligence).map(([ticker, value]) => {
          const item = asObject(value);
          const analysis = asObject(item?.analysis);
          return <div key={ticker}>
            <strong>{ticker}</strong> · {asText(item?.status) ?? 'UNKNOWN'}
            {asText(analysis?.summary) && <p>{asText(analysis?.summary)}</p>}
          </div>;
        })}
      </details>}

      {deterministicSummary && seniorSummary && deterministicSummary !== seniorSummary && <details>
        <summary>Resumo determinístico do motor</summary>
        <p>{deterministicSummary}</p>
      </details>}
    </section>}

    {!summary && positions.length > 0 && <section className="analysis-section">
      <h4>Carteira canônica</h4>
      <p>{positions.length} posições no snapshot{asOf ? ` de ${asOf}` : ''}.</p>
      {(assignmentCapital != null || uncoveredCallShares != null) && <p>
        {assignmentCapital != null ? `Capital potencial de exercício/assign: ${brl(assignmentCapital)}.` : ''}
        {uncoveredCallShares != null ? ` Ações descobertas em calls: ${uncoveredCallShares}.` : ''}
      </p>}
    </section>}

    {rankedOpportunities.length > 0 && <section className="analysis-section">
      <h4>Oportunidades canônicas</h4>
      <p className="muted">
        Ranking determinístico · política {asText(opportunitySet?.ranking_policy_version) ?? 'não informada'}.
        A inteligência dos agentes interpreta estes fatos, mas não altera a ordem canônica.
      </p>
      <div className="evidence-grid">
        {rankedOpportunities.slice(0, 10).map((item, index) => {
          const optionId = asText(item.options_analysis_ref);
          const marketability = optionId && optionMarketability
            ? asObject(optionMarketability[optionId])
            : null;
          const expectedReturn = numberValue(item.expected_return);
          const capital = numberValue(item.capital_requirement);
          const bid = numberValue(marketability?.bid);
          const ask = numberValue(marketability?.ask);
          const volume = numberValue(marketability?.volume);
          return <article className="evidence-card" key={asText(item.opportunity_id) ?? String(index)}>
            <h5>{asText(item.ticker) ?? 'Ativo'} · {asText(item.action) ?? 'Ação'}</h5>
            <dl>
              {optionId && <div><dt>Contrato</dt><dd>{optionId}</dd></div>}
              <div><dt>Retorno anualizado</dt><dd>{pct(expectedReturn) ?? 'Indisponível'}</dd></div>
              <div><dt>Capital requerido</dt><dd>{brl(capital) ?? 'Indisponível'}</dd></div>
              <div><dt>Atratividade</dt><dd>{asText(item.attractiveness) ?? 'UNKNOWN'}</dd></div>
              <div><dt>Fit carteira</dt><dd>{asText(item.portfolio_fit) ?? 'UNKNOWN'}</dd></div>
              {marketability && <>
                <div><dt>Bid atual</dt><dd>{brl(bid) ?? 'Indisponível'}</dd></div>
                <div><dt>Ask atual</dt><dd>{brl(ask) ?? 'Indisponível'}</dd></div>
                <div><dt>Volume</dt><dd>{volume == null ? 'Indisponível' : new Intl.NumberFormat('pt-BR').format(volume)}</dd></div>
              </>}
            </dl>
          </article>;
        })}
      </div>
    </section>}

    {broadMarketDiagnostics.length > 0 && broadMarketResearch.length === 0 && <details>
      <summary>Diagnóstico da pesquisa de mercado</summary>
      {broadMarketDiagnostics.map((value, index) => {
        const row = asObject(value);
        return <p key={index} className="muted">
          {asText(row?.query) ?? 'consulta'} · resultados normalizados: {numberValue(row?.normalized_result_count) ?? 0}
          {asText(row?.error) ? ` · erro: ${asText(row?.error)}` : ''}
        </p>;
      })}
    </details>}

    {evidenceEntries.length > 0 && <section className="analysis-section">
      <h4>Fatos determinísticos por ativo</h4>
      <div className="evidence-grid">
        {evidenceEntries.map(([ticker, evidence]) => {
          const market = asObject(evidence.market);
          const currentQuote = asObject(market?.current_quote);
          const historyLatest = asObject(market?.history_latest) ?? asObject(market?.latest);
          const previousCompleted = asObject(market?.previous_completed_close);
          const quant = asObject(evidence.quant);
          const fundamentals = asObject(evidence.fundamentals);
          const portfolio = asObject(evidence.portfolio);
          const currentPrice = numberValue(currentQuote?.close);
          const currentVolume = numberValue(currentQuote?.volume);
          const historyClose = numberValue(historyLatest?.close);
          const previousClose = numberValue(previousCompleted?.close);
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
              <div><dt>Preço atual</dt><dd>{brl(currentPrice) ?? 'Indisponível'}</dd></div>
              <div><dt>Cotação atual</dt><dd>{currentQuote ? `${String(currentQuote.source ?? 'fonte desconhecida')} · ${when(currentQuote.observation_timestamp)}` : 'Indisponível'}</dd></div>
              <div><dt>Volume atual</dt><dd>{currentVolume == null ? 'Indisponível' : new Intl.NumberFormat('pt-BR').format(currentVolume)}</dd></div>
              <div><dt>Fechamento anterior concluído</dt><dd>{brl(previousClose) ?? 'Indisponível'}</dd></div>
              <div><dt>Candle histórico mais recente</dt><dd>{brl(historyClose) ?? 'Indisponível'}</dd></div>
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

    {optionEvidenceEntries.length > 0 && <section className="analysis-section">
      <h4>Cotações atuais de opções · OPLAB</h4>
      <div className="evidence-grid">
        {optionEvidenceEntries.map(([optionId, evidence]) => {
          const contract = asObject(evidence.contract);
          const quote = asObject(evidence.current_quote);
          const put = asObject(evidence.put_analysis);
          const marketability = asObject(evidence.marketability);
          const bid = numberValue(quote?.bid);
          const ask = numberValue(quote?.ask);
          const last = numberValue(quote?.last);
          const mid = numberValue(quote?.mid);
          const volume = numberValue(quote?.volume);
          const strike = numberValue(contract?.strike);
          const effectivePrice = numberValue(put?.effective_price);
          const annualized = numberValue(put?.annualized_return);
          const spreadAbs = numberValue(marketability?.spread_abs);
          const spreadPct = numberValue(marketability?.spread_pct_of_mid);
          return <article className="evidence-card" key={optionId}>
            <h5>{optionId}</h5>
            <dl>
              <div><dt>Ativo</dt><dd>{asText(evidence.underlying_ticker) ?? '—'}</dd></div>
              <div><dt>Strike</dt><dd>{brl(strike) ?? 'Indisponível'}</dd></div>
              <div><dt>Vencimento</dt><dd>{asText(contract?.expiration_date) ?? 'Indisponível'}</dd></div>
              <div><dt>Bid atual</dt><dd>{brl(bid) ?? 'Indisponível'}</dd></div>
              <div><dt>Ask atual</dt><dd>{brl(ask) ?? 'Indisponível'}</dd></div>
              <div><dt>Último negócio</dt><dd>{brl(last) ?? 'Indisponível'}</dd></div>
              <div><dt>Mid</dt><dd>{brl(mid) ?? 'Indisponível'}</dd></div>
              <div><dt>Volume</dt><dd>{volume == null ? 'Indisponível' : new Intl.NumberFormat('pt-BR').format(volume)}</dd></div>
              <div><dt>Executável para venda</dt><dd>{marketability?.executable_for_sell === true ? 'Sim' : 'Não'}</dd></div>
              <div><dt>Mercado bilateral</dt><dd>{marketability?.two_sided_market === true ? 'Sim' : 'Não'}</dd></div>
              <div><dt>Spread bid/ask</dt><dd>{spreadAbs == null ? 'Indisponível' : `${brl(spreadAbs)}${spreadPct == null ? '' : ` · ${pct(spreadPct)} do mid`}`}</dd></div>
              <div><dt>Liquidez</dt><dd>{asText(marketability?.liquidity_assessment) === 'not_scored_without_versioned_policy' ? 'Não pontuada (política ainda não versionada)' : 'Indisponível'}</dd></div>
              <div><dt>Preço efetivo se exercida</dt><dd>{brl(effectivePrice) ?? 'Indisponível'}</dd></div>
              <div><dt>Retorno anualizado do prêmio</dt><dd>{pct(annualized) ?? 'Indisponível'}</dd></div>
              <div><dt>Cotação</dt><dd>{quote ? `${String(quote.source ?? 'fonte desconhecida')} · ${when(quote.observation_timestamp)}` : 'Indisponível'}</dd></div>
            </dl>
          </article>;
        })}
      </div>
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
