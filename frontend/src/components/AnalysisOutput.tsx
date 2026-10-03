import ResearchEvidence from './ResearchEvidence';
import PersonalHistory from './PersonalHistory';
import DecisionHistory from './DecisionHistory';
import CanonicalExperience from './CanonicalExperience';
import type { OrchestrateResponse } from '../api/contracts';

type Obj = Record<string, unknown>;
const scenarioCapitalBasisLabels: Record<string, string> = {
  explicit_comparison_amount: 'valor de compra informado',
  cash_secured_strike_notional: 'colateral calculado pelo strike',
  one_covered_contract_underlying_notional: 'valor de uma cobertura de contrato',
  known_current_stock_position_market_value: 'valor de mercado conhecido da posição',
  UNKNOWN: 'desconhecida',
};

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
  const scenarioAnalysis = asObject(result.scenario_analysis);
  const putChainComparison = asObject(result.put_chain_comparison);
  const putChainCandidates = asArray(putChainComparison?.candidates)
    .map(asObject)
    .filter((item): item is Obj => item !== null);
  const putChainRanking = asObject(putChainComparison?.ranking);
  const scenarioObjectivePolicy = asObject(scenarioAnalysis?.objective_policy);
  const scenarioAlternatives = asArray(scenarioAnalysis?.alternatives)
    .map(asObject)
    .filter((item): item is Obj => item !== null);
  const scenarioWinnerId = asText(scenarioObjectivePolicy?.ranked_alternative_id);
  const scenarioWinner = scenarioAlternatives.find(item => asText(item.alternative_id) === scenarioWinnerId);
  const scenarioWorstReturns = asObject(scenarioObjectivePolicy?.worst_case_return_pct_by_alternative);
  const workspaceIntelligence = asObject(result.workspace_intelligence);
  const workspaceName = asText(workspaceIntelligence?.workspace);
  const workspaceLimitations = asStrings(workspaceIntelligence?.limitations);
  const opportunityLimitations = asStrings(result.opportunity_limitations);
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
  const opportunityRankingStatus = asText(result.opportunity_ranking_status);
  const opportunityRankingReason = asText(result.opportunity_ranking_reason);
  const rankedOpportunities = asArray(opportunitySet?.ranked_opportunities)
    .map(asObject)
    .filter((item): item is Obj => item !== null);
  const optionMarketability = asObject(result.option_marketability);
  const assetEvidence = asObject(result.asset_evidence);
  const optionEvidence = asObject(result.option_evidence);
  const strategyAlternatives = asArray(strategyComparison?.alternatives)
    .map(asObject)
    .filter((item): item is Obj => item !== null);
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
  const limitations = [...asStrings(result.limitations), ...workspaceLimitations, ...opportunityLimitations];
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
    {asText(result.derived_synthesis_status) === 'PENDING' && <p className="muted" role="status">Fatos disponíveis. Síntese em andamento…</p>}
    {asText(result.derived_synthesis_status) === 'FAILED' && <div className="state-banner limited">Síntese indisponível. Os fatos determinísticos continuam disponíveis com suas fontes e limitações.</div>}

    {summary && <section className="analysis-summary"><h3>Resumo</h3><p>{summary}</p></section>}

    {rationale && <section className="analysis-section"><h4>Racional</h4><p>{rationale}</p></section>}
    {workspaceName === 'Opportunities' && rankedOpportunities.length === 0 && <div className="state-banner limited">
      <strong>Sem ranking disponível</strong>
      <span>{opportunityRankingReason ?? (opportunitySet ? 'O pipeline não retornou candidatos canônicos nesta execução.' : 'O pipeline canônico não retornou um conjunto de oportunidades.')}{opportunityRankingStatus ? ` · estado ${opportunityRankingStatus}` : ''}</span>
    </div>}
    {workspaceName === 'Strategy Lab' && strategyAlternatives.length === 0 && <div className="state-banner limited">
      <strong>Comparação não calculada</strong>
      <span>O backend não forneceu alternativas determinísticas nesta execução. O sistema não declara vencedor sem cotações e métricas comparáveis.</span>
    </div>}
    {workspaceName === 'Market Intelligence' && !summary && workspaceLimitations.length > 0 && <div className="state-banner limited">
      <strong>Inteligência limitada</strong>
      <span>{workspaceLimitations.join(' · ')}</span>
    </div>}

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
        {opportunityRankingStatus === 'DEFERRED_INCOMPLETE_CONTEXT'
          ? 'Ranking econômico adiado · candidatos em ordenação técnica reproduzível'
          : 'Ranking determinístico'}
        {' · '}política {asText(opportunitySet?.ranking_policy_version) ?? 'não informada'}.
        A inteligência dos agentes interpreta estes fatos, mas não altera a ordem canônica.
      </p>
      {opportunityRankingReason && <p className="muted">{opportunityRankingReason}</p>}
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
          const dte = numberValue(marketability?.days_to_expiration);
          const premiumYield = numberValue(marketability?.premium_yield);
          const spreadPct = numberValue(marketability?.spread_pct_of_mid);
          const effectivePrice = numberValue(marketability?.effective_price);
          const optionType = asText(marketability?.option_type);
          const gainToStrike = numberValue(marketability?.gain_to_strike);
          const totalReturnIfAssigned = numberValue(marketability?.total_return_if_assigned);
          const coveredCall = marketability?.covered_call === true;
          const coveredRequired = numberValue(marketability?.covered_shares_required);
          const stockAvailable = numberValue(marketability?.stock_shares_available);
          const coveredPositionValue = numberValue(marketability?.covered_position_value);
          const incrementalCapital = numberValue(marketability?.incremental_capital_required);
          return <article className="evidence-card" key={asText(item.opportunity_id) ?? String(index)}>
            <h5>{asText(item.ticker) ?? 'Ativo'} · {asText(item.action) ?? 'Ação'}</h5>
            <dl>
              {optionId && <div><dt>Contrato</dt><dd>{optionId}</dd></div>}
              <div><dt>Retorno anualizado</dt><dd>{pct(expectedReturn) ?? 'Indisponível'}{opportunityRankingStatus === 'DEFERRED_INCOMPLETE_CONTEXT' ? ' · evidência, não ranking' : ''}</dd></div>
              <div><dt>Retorno do prêmio</dt><dd>{pct(premiumYield) ?? 'Indisponível'}</dd></div>
              <div><dt>DTE</dt><dd>{dte == null ? 'Indisponível' : dte.toFixed(0)}</dd></div>
              {effectivePrice != null && <div><dt>Preço efetivo</dt><dd>{brl(effectivePrice)}</dd></div>}
              {optionType === 'CALL' && <div><dt>Ganho até strike</dt><dd>{brl(gainToStrike) ?? 'Indisponível'}</dd></div>}
              {optionType === 'CALL' && <div><dt>Retorno se exercida</dt><dd>{pct(totalReturnIfAssigned) ?? 'Indisponível'}</dd></div>}
              {optionType === 'CALL' && <div><dt>Cobertura</dt><dd>{coveredCall && coveredRequired != null && stockAvailable != null ? `${coveredRequired} ações requeridas · ${stockAvailable} disponíveis` : 'Não confirmada'}</dd></div>}
              {optionType === 'CALL'
                ? <>
                    <div><dt>Capital já coberto pelas ações</dt><dd>{brl(coveredPositionValue ?? capital) ?? 'Indisponível'}</dd></div>
                    <div><dt>Capital incremental</dt><dd>{brl(incrementalCapital ?? 0)}</dd></div>
                  </>
                : <div><dt>Capital requerido</dt><dd>{brl(capital) ?? 'Indisponível'}</dd></div>}
              <div><dt>Atratividade</dt><dd>{asText(item.attractiveness) ?? 'UNKNOWN'}</dd></div>
              <div><dt>Fit carteira</dt><dd>{asText(item.portfolio_fit) ?? 'UNKNOWN'}</dd></div>
              {marketability && <>
                <div><dt>Bid atual</dt><dd>{brl(bid) ?? 'Indisponível'}</dd></div>
                <div><dt>Ask atual</dt><dd>{brl(ask) ?? 'Indisponível'}</dd></div>
                <div><dt>Spread/mid</dt><dd>{pct(spreadPct) ?? 'Indisponível'}</dd></div>
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
              <div><dt>Na carteira</dt><dd>{held ? `Sim${quantity != null ? ` · ${quantity} ações` : ''}` : portfolio?.held === false ? 'Não' : 'Indisponível'}</dd></div>
            </dl>
          </article>;
        })}
      </div>
      {strategyComparison && <p className="muted">
        Comparação determinística disponível. O ranking econômico geral continua {asText(asObject(strategyComparison.assumptions)?.ranking) ?? 'não aplicado'}; o critério condicional de cenários aparece separadamente abaixo quando solicitado.
      </p>}
    </section>}

    {strategyAlternatives.length > 0 && <section className="analysis-section">
      <h4>Alternativas comparadas</h4>
      <div className="evidence-grid">
        {strategyAlternatives.map((item, index) => {
          const assumptions = asObject(item.assumptions);
          const actionType = asText(item.action_type);
          const capitalRequired = numberValue(item.capital_required);
          const capitalReleased = numberValue(assumptions?.capital_released);
          const quantityBefore = numberValue(assumptions?.stock_quantity_before);
          const quantityAfter = numberValue(assumptions?.stock_quantity_after_theoretical);
          const sharesReduced = numberValue(assumptions?.theoretical_shares_reduced);
          return <article className="evidence-card" key={asText(item.alternative_id) ?? String(index)}>
            <h5>{asText(item.label) ?? actionType ?? 'Alternativa'}</h5>
            <dl>
              <div><dt>Ação</dt><dd>{actionType ?? 'Indisponível'}</dd></div>
              <div><dt>Capital requerido</dt><dd>{brl(capitalRequired) ?? 'Indisponível'}</dd></div>
              {capitalReleased != null && <div><dt>Capital liberado no what-if</dt><dd>{brl(capitalReleased)}</dd></div>}
              {quantityBefore != null && <div><dt>Ações antes</dt><dd>{quantityBefore.toLocaleString('pt-BR')}</dd></div>}
              {sharesReduced != null && <div><dt>Redução teórica</dt><dd>{sharesReduced.toLocaleString('pt-BR',{maximumFractionDigits:2})} ações</dd></div>}
              {quantityAfter != null && <div><dt>Ações após what-if</dt><dd>{quantityAfter.toLocaleString('pt-BR',{maximumFractionDigits:2})}</dd></div>}
            </dl>
            {asText(assumptions?.execution_quantity) === 'not_inferred' && <p className="muted">Quantidade executável não inferida; comparação por nocional.</p>}
          </article>;
        })}
      </div>
    </section>}

    {scenarioAnalysis && (asText(scenarioAnalysis.status) !== 'NOT_REQUESTED' || asText(scenarioObjectivePolicy?.requested_objective) !== 'COMPARE_ONLY') && <section className="analysis-section">
      <h4>Cenários determinísticos · {asText(scenarioAnalysis.status) ?? 'indisponível'}</h4>
      <p className="muted">Horizonte: {asText(scenarioAnalysis.horizon) ?? 'Indisponível'} · Choques informados pelo usuário; probabilidades permanecem indisponíveis.</p>
      {asText(scenarioObjectivePolicy?.requested_objective) === 'MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL' && <p className="muted">Objetivo: maximizar o menor retorno sobre a base de capital informada/observada, somente dentro dos cenários fornecidos. Resultado: {asText(scenarioObjectivePolicy?.status) ?? 'indisponível'}.</p>}
      {asText(scenarioObjectivePolicy?.status) === 'CONDITIONAL_RANKING' && <p className="state-banner limited">Sob estes cenários e bases de capital, {asText(scenarioWinner?.label) ?? scenarioWinnerId ?? 'a alternativa selecionada'} tem o maior retorno no pior cenário ({pct(numberValue(scenarioWorstReturns?.[scenarioWinnerId ?? '']) == null ? null : numberValue(scenarioWorstReturns?.[scenarioWinnerId ?? ''])! / 100) ?? 'Indisponível'}); isso não é previsão nem recomendação universal.</p>}
      {asText(scenarioObjectivePolicy?.status) === 'TIE' && <p className="state-banner limited">As alternativas empatam pelo critério selecionado dentro dos cenários informados.</p>}
      {asText(scenarioObjectivePolicy?.status) === 'UNAVAILABLE' && <p className="muted">Ranking condicional indisponível: {asText(scenarioObjectivePolicy?.reason) ?? 'dados insuficientes'}.</p>}
      <div className="evidence-grid">
        {scenarioAlternatives.map((item, index) => {
          const payoffs = asObject(item.pnl_by_scenario_brl);
          const returns = asObject(item.return_by_scenario_pct);
          const terminalPrices = asObject(item.terminal_underlying_price_by_scenario);
          return <article className="evidence-card" key={asText(item.alternative_id) ?? String(index)}>
            <h5>{asText(item.label) ?? 'Alternativa'}</h5>
            {asText(item.pnl_basis) && <p className="muted">Base do P&amp;L: {asText(item.pnl_basis)}</p>}
            <dl><div><dt>Base de capital</dt><dd>{brl(numberValue(item.capital_basis_brl)) ?? 'Indisponível'} · {scenarioCapitalBasisLabels[asText(item.capital_basis_source) ?? 'UNKNOWN'] ?? 'desconhecida'}</dd></div>
              {Object.entries(payoffs ?? {}).map(([scenario, value]) => <div key={scenario}>
              <dt>{scenario}{numberValue(terminalPrices?.[scenario]) == null ? '' : ` · subjacente ${brl(numberValue(terminalPrices?.[scenario]))}`}</dt><dd>{brl(numberValue(value)) ?? 'Indisponível'}{numberValue(returns?.[scenario]) == null ? '' : ` · ${pct(numberValue(returns?.[scenario])! / 100)}`}</dd>
            </div>)}</dl>
            {!Object.keys(payoffs ?? {}).length && <p className="muted">Payoff indisponível com os dados/horizonte recebidos.</p>}
          </article>;
        })}
      </div>
      {asStrings(scenarioAnalysis.limitations).length > 0 && <ul>{asStrings(scenarioAnalysis.limitations).map((item, index) => <li key={index}>{item}</li>)}</ul>}
    </section>}

    {putChainComparison && <section className="analysis-section">
      <h4>PUTs do mesmo vencimento · {asText(putChainComparison.ticker) ?? 'ativo'} · {asText(putChainComparison.expiration_date) ?? 'vencimento indisponível'}</h4>
      <p className="muted">Cotação da cadeia: {when(putChainComparison.quote_snapshot_as_of)} · Subjacente: {brl(numberValue(putChainComparison.underlying_price)) ?? 'Indisponível'} · Política {asText(putChainComparison.policy_version) ?? 'não informada'}.</p>
      {putChainRanking && asText(putChainRanking.requested_objective) === 'MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL' && <p className="muted">Ranking maximin: {asText(putChainRanking.status) ?? 'indisponível'}{asText(putChainRanking.ranked_option_id) ? ` · ${asText(putChainRanking.ranked_option_id)}` : ''}{asText(putChainRanking.reason) ? ` · ${asText(putChainRanking.reason)}` : ''}. Critério limitado aos choques informados.</p>}
      <div className="evidence-grid">
        {putChainCandidates.map((item, index) => {
          const contract = asObject(item.contract);
          const quote = asObject(item.quote);
          const probabilities = asObject(item.probability_estimates);
          const style = asObject(item.exercise_style);
          const early = asObject(item.early_assignment);
          const personal = asObject(item.personal_assignment_frequency);
          const payoffs = asObject(item.pnl_by_scenario_brl);
          const returns = asObject(item.return_by_scenario_pct);
          return <article className="evidence-card" key={asText(contract?.option_id) ?? String(index)}>
            <h5>{asText(contract?.option_id) ?? 'Contrato'} · strike {brl(numberValue(contract?.strike)) ?? 'Indisponível'}</h5>
            <p className="muted">Fonte: {asText(quote?.source) ?? 'UNKNOWN'} · registro {asText(quote?.source_record_id) ?? 'UNKNOWN'}</p>
            <dl>
              <div><dt>Bid / ask / mid</dt><dd>{brl(numberValue(quote?.bid)) ?? 'Indisponível'} / {brl(numberValue(quote?.ask)) ?? 'Indisponível'} / {brl(numberValue(quote?.mid)) ?? 'Indisponível'}</dd></div>
              <div><dt>Prêmio / break-even</dt><dd>{brl(numberValue(item.premium_total_one_contract)) ?? 'Indisponível'} por contrato · {brl(numberValue(item.breakeven_price)) ?? 'Indisponível'} por ação</dd></div>
              <div><dt>Colateral / perda máxima antes de custos</dt><dd>{brl(numberValue(item.capital_required_one_contract)) ?? 'Indisponível'} / {brl(numberValue(item.maximum_loss_one_contract_before_costs)) ?? 'Indisponível'}</dd></div>
              <div><dt>Spread / volume / OI</dt><dd>{brl(numberValue(item.spread_abs)) ?? 'Indisponível'} · {numberValue(item.volume)?.toLocaleString('pt-BR') ?? 'UNKNOWN'} · {numberValue(item.open_interest)?.toLocaleString('pt-BR') ?? 'UNKNOWN'}</dd></div>
              <div><dt>IV / delta</dt><dd>{numberValue(quote?.implied_volatility) == null ? 'UNKNOWN' : pct(numberValue(quote?.implied_volatility))} · {numberValue(quote?.delta) == null ? 'UNKNOWN' : numberValue(quote?.delta)?.toLocaleString('pt-BR')}</dd></div>
              <div><dt>P(ITM) no vencimento / P(touch)</dt><dd>{numberValue(probabilities?.expiry_itm_probability) == null ? 'UNKNOWN' : pct(numberValue(probabilities?.expiry_itm_probability))} / {numberValue(probabilities?.touch_probability) == null ? 'UNKNOWN' : pct(numberValue(probabilities?.touch_probability))} · {asText(probabilities?.status) ?? 'UNKNOWN'}</dd></div>
              <div><dt>Modelo</dt><dd>{asText(probabilities?.model) ?? 'Indisponível'} · calibração {asText(probabilities?.calibration_status) ?? 'UNKNOWN'}</dd></div>
              <div><dt>Estilo de exercício</dt><dd>{asText(style?.normalized) ?? 'UNKNOWN'} · {asText(style?.status) ?? 'UNKNOWN'}</dd></div>
              <div><dt>Assignment antecipado</dt><dd>{asText(early?.status) ?? 'UNKNOWN'} · {asText(early?.reason) ?? 'Sem base disponível'}</dd></div>
              <div><dt>Frequência pessoal</dt><dd>{asText(personal?.status) ?? 'UNKNOWN'} · denominador {numberValue(personal?.eligible_denominator)?.toLocaleString('pt-BR') ?? 'UNKNOWN'}</dd></div>
              {Object.entries(payoffs ?? {}).map(([scenario, value]) => <div key={scenario}><dt>{scenario}</dt><dd>{brl(numberValue(value)) ?? 'Indisponível'}{numberValue(returns?.[scenario]) == null ? '' : ` · ${pct(numberValue(returns?.[scenario])! / 100)}`}</dd></div>)}
            </dl>
            {asText(personal?.reason) && <p className="muted">{asText(personal?.reason)}</p>}
          </article>;
        })}
      </div>
      {asStrings(putChainComparison.limitations).length > 0 && <ul>{asStrings(putChainComparison.limitations).map((item, index) => <li key={index}>{item}</li>)}</ul>}
    </section>}

    {optionEvidenceEntries.length > 0 && <section className="analysis-section">
      <h4>Cotações atuais de opções · OPLAB</h4>
      <div className="evidence-grid">
        {optionEvidenceEntries.map(([optionId, evidence]) => {
          const contract = asObject(evidence.contract);
          const quote = asObject(evidence.current_quote);
          const put = asObject(evidence.put_analysis);
          const call = asObject(evidence.call_analysis);
          const marketability = asObject(evidence.marketability);
          const bid = numberValue(quote?.bid);
          const ask = numberValue(quote?.ask);
          const last = numberValue(quote?.last);
          const mid = numberValue(quote?.mid);
          const volume = numberValue(quote?.volume);
          const strike = numberValue(contract?.strike);
          const effectivePrice = numberValue(put?.effective_price);
          const premiumReturn = numberValue(call?.premium_return);
          const annualized =
            numberValue(put?.annualized_return) ??
            numberValue(call?.annualized_premium_return);
          const gainToStrike = numberValue(call?.gain_to_strike);
          const totalReturnIfAssigned = numberValue(call?.total_return_if_assigned);
          const coveredRequired = numberValue(evidence.covered_shares_required);
          const stockAvailable = numberValue(evidence.stock_shares_available);
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
              {put && <div><dt>Preço efetivo se exercida</dt><dd>{brl(effectivePrice) ?? 'Indisponível'}</dd></div>}
              {call && <div><dt>Retorno do prêmio</dt><dd>{pct(premiumReturn) ?? 'Indisponível'}</dd></div>}
              {call && <div><dt>Ganho até o strike</dt><dd>{brl(gainToStrike) ?? 'Indisponível'}</dd></div>}
              {call && <div><dt>Retorno se exercida</dt><dd>{pct(totalReturnIfAssigned) ?? 'Indisponível'}</dd></div>}
              {call && <div><dt>Cobertura</dt><dd>{coveredRequired == null || stockAvailable == null ? 'Indisponível' : `${coveredRequired} ações requeridas · ${stockAvailable} disponíveis`}</dd></div>}
              <div><dt>Retorno anualizado do prêmio</dt><dd>{pct(annualized) ?? 'Indisponível'}</dd></div>
              <div><dt>Cotação</dt><dd>{quote ? `${String(quote.source ?? 'fonte desconhecida')} · ${when(quote.observation_timestamp)}` : 'Indisponível'}</dd></div>
            </dl>
          </article>;
        })}
      </div>
    </section>}

    <ResearchEvidence stored={result.stored_research} market={result.research_context} />
    <DecisionHistory value={result.decision_history} />
    <CanonicalExperience value={result.canonical_experience_context} />
    {asArray(asObject(result.decision_history)?.candidates).length ? <details><summary>Histórico geral do ativo — inclui raízes de opções não verificadas</summary><PersonalHistory value={result.personal_history} /></details> : <PersonalHistory value={result.personal_history} />}

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
