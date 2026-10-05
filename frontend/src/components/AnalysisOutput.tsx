import {lazy,Suspense} from 'react';
import {date,State} from './cockpit';
const ScenarioChart=lazy(()=>import('./ScenarioChart'));
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

const fundamentalLabels: Record<string, string> = {
  currentRatio: 'Liquidez corrente',
  quickRatio: 'Liquidez imediata',
  debtToEquity: 'Dívida sobre patrimônio líquido',
  earningsGrowth: 'Crescimento do lucro · TTM',
  earningsGrowthAnnual: 'Crescimento anual do lucro',
  freeCashflow: 'Fluxo de caixa livre',
  operatingCashflow: 'Fluxo de caixa operacional',
  grossMargins: 'Margem bruta',
  profitMargins: 'Margem líquida',
  operatingMargins: 'Margem operacional',
  grossProfits: 'Lucro bruto',
  returnOnEquity: 'Retorno sobre patrimônio líquido (ROE)',
  returnOnAssets: 'Retorno sobre ativos (ROA)',
  priceEarnings: 'Preço / lucro (P/L)',
  priceToBook: 'Preço / valor patrimonial (P/VP)',
  earningsPerShare: 'Lucro por ação (LPA)',
  marketCap: 'Valor de mercado',
  dividendYield: 'Dividend yield informado pela fonte',
};
const fundamentalLabel = (key: string) =>
  fundamentalLabels[key] ?? key.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/^./, value => value.toUpperCase());
const fundamentalDisplay = (key: string, metric: Obj | null): string => {
  const value = numberValue(metric?.value);
  if (value == null) return 'Sem valor elegível';
  const unit = asText(metric?.unit);
  const proportional = /^(earningsGrowth|earningsGrowthAnnual|grossMargins|profitMargins|operatingMargins|returnOnEquity|returnOnAssets|dividendYield)$/i.test(key);
  if (proportional) return pct(value) ?? 'Indisponível';
  if (unit === 'ratio') return `${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}×`;
  if (unit === 'BRL' || unit === 'BRL/share') return brl(value) ?? 'Indisponível';
  if (unit === 'percent') return `${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`;
  return `${value.toLocaleString('pt-BR', { maximumFractionDigits: 4 })}${unit ? ` ${unit}` : ' · unidade não informada'}`;
};

const numberValue = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;

const brl = (value: number | null) =>
  value == null ? null : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);

const strategyMetrics: {label: string; key: string; format: (value: number | null) => string | null}[] = [
  {label: 'Capital requerido', key: 'capital_required', format: value => brl(value)},
  {label: 'Retorno esperado informado pelo motor', key: 'expected_return', format: value => pct(value)},
  {label: 'Perda máxima modelada', key: 'max_loss', format: value => brl(value)},
  {label: 'Score de liquidez (0–1)', key: 'liquidity_score', format: value => value == null ? null : value.toLocaleString('pt-BR')},
  {label: 'Impacto na carteira informado pelo motor', key: 'portfolio_impact', format: value => value == null ? null : value.toLocaleString('pt-BR')},
];

const pct = (value: number | null) =>
  value == null ? null : new Intl.NumberFormat('pt-BR', { style: 'percent', maximumFractionDigits: 2 }).format(value);

const when = date;

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
  const economic = asObject(result.economic_decision);
  const economicRows = asArray(economic?.rows).map(asObject).filter((row):row is Obj=>row!==null);
  const stockPurchase = asObject(result.stock_purchase_comparison);
  const stockPurchaseRows = asArray(stockPurchase?.rows).map(asObject).filter((row):row is Obj=>row!==null);
  const putPair = asObject(result.put_pair_comparison);
  const putPairRows = asArray(putPair?.rows).map(asObject).filter((row):row is Obj=>row!==null);
  const fundedSwitch = asObject(result.funded_switch);
  const opportunityScreen = asObject(result.opportunity_screen);
  const screenedRows = asArray(opportunityScreen?.rows).map(asObject).filter((item): item is Obj => item !== null);
  const screeningReasons: Record<string, string> = {
    HISTORY_PROVIDER_UNAVAILABLE:'Histórico indisponível na fonte', CURRENT_QUOTE_UNAVAILABLE:'Cotação atual indisponível',
    FUNDAMENTALS_UNAVAILABLE:'Fundamentos indisponíveis', INVALID_HISTORY_VALUE:'Histórico contém valores inválidos',
    DUPLICATE_HISTORY_OBSERVATIONS:'Observações duplicadas no histórico', INSUFFICIENT_OBJECTIVE_SAMPLE:'Amostra insuficiente para o objetivo',
    STALE_OBJECTIVE_WINDOW:'Última observação há mais de 7 dias · fora da ordenação',
    NONCOMPARABLE_OBSERVATION_WINDOW:'Janela de observações diferente da população comparável',
  };
  const screenStatus: Record<string, string> = {
    RANKED_CONDITIONALLY:'Ordenação condicional disponível', PARTIAL_COMPARABLE_UNIVERSE:'Ordenação parcial · há ativos não comparáveis',
    INSUFFICIENT_COMPARABLE_ASSETS:'Menos de dois ativos comparáveis · sem ranking', COMPARED_WITHOUT_RANKING:'Comparação sem ranking',
  };
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
  const stockPurchaseByTicker = new Map(stockPurchaseRows.map(row => [asText(row.ticker) ?? '', row]));
  const stockComparisonTickers = strategyAlternatives.map(item => asText(item.subject_id)).filter((ticker): ticker is string => Boolean(ticker));
  const stockPurchaseTickers = stockComparisonTickers.length === 2
    ? stockComparisonTickers
    : stockPurchaseRows.map(row => asText(row.ticker)).filter((ticker): ticker is string => Boolean(ticker));
  const historicalComparisons = asArray(stockPurchase?.historical_comparisons).map(asObject).filter((row):row is Obj=>row!==null);
  const fundamentalComparisons = asArray(stockPurchase?.fundamental_comparisons).map(asObject).filter((row):row is Obj=>row!==null);
  const fundamentalMetricNames = [...new Set(stockPurchaseRows.flatMap(row => [
    ...Object.keys(asObject(row.fundamental_metrics) ?? {}),
    ...asArray(row.excluded_metrics).map(asObject).map(item => asText(item?.metric)).filter((name):name is string => Boolean(name)),
  ]))].sort((a,b) => fundamentalLabel(a).localeCompare(fundamentalLabel(b), 'pt-BR'));
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
  const resultQuality = asText(result.quality_status);
  const portfolioQuality = asText(portfolioContext?.quality_status);
  const assignmentCapital = numberValue(capitalRisk?.assignment_capital);
  const uncoveredCallShares = numberValue(capitalRisk?.uncovered_call_shares);

  return <div className="output human-output">
    <div className="analysis-status">
      <strong>{data.status}</strong>
      {resultQuality && <span title="Status informado pelo motor; consulte conflitos e lacunas para avaliar a cobertura das evidências.">Validação do resultado: {resultQuality}</span>}
      {portfolioQuality && <span>Qualidade da carteira: {portfolioQuality}</span>}
      {asOf && <span>Dados de {when(asOf)} · São Paulo</span>}
      {asText(fastRoute?.target) && <span>Rota: {asText(fastRoute?.target)}</span>}
    </div>

    {data.error && <div className="state-banner error">{data.error}</div>}
    {asText(result.derived_synthesis_status) === 'PENDING' && <p className="muted" role="status">Fatos disponíveis. Síntese em andamento…</p>}
    {asText(result.derived_synthesis_status) === 'FAILED' && <div className="state-banner limited">Síntese indisponível. Os fatos determinísticos continuam disponíveis com suas fontes e limitações.</div>}

    {summary && <section className="analysis-summary"><h3>Resumo</h3><p>{summary}</p></section>}

    {economic&&<section className="analysis-section"><h3>Decisão econômica · compras com capital comparável</h3><p>{economic.ranking==='CONDITIONAL_USER_SCENARIOS_ONLY'?'Preferência condicional ao pior cenário informado':economic.ranking==='TIE'?'Empate nos cenários informados':economic.ranking==='UNKNOWN_INCOMPLETE_INPUTS'?'Dados incompletos: sem preferência líquida':'Comparação sem preferência'} · {asText(economic.horizon)??'Horizonte não informado'}</p><div className="table-wrap"><table><thead><tr><th>Ação / ordem condicional</th><th>Orçamento</th><th>Quantidade inteira</th><th>Compra / custo de entrada</th><th>Caixa residual</th><th>Distribuição observada 365d / preço atual</th></tr></thead><tbody>{economicRows.map(row=><tr key={asText(row.alternative_id)}><td>{asText(row.ticker)} / {numberValue(row.rank)??'—'}</td><td>{brl(numberValue(row.budget_brl))??'UNKNOWN'}</td><td>{numberValue(row.quantity)??'UNKNOWN'}</td><td>{brl(numberValue(row.purchase_notional_brl))??'UNKNOWN'} / {brl(numberValue(row.entry_costs_brl))??'UNKNOWN'}</td><td>{brl(numberValue(row.residual_cash_brl))??'UNKNOWN'}</td><td>{pct(numberValue(row.observed_distribution_yield_365d_fraction))??'UNKNOWN'}<small>Cobertura não comprovada; não é dividend yield futuro</small></td></tr>)}</tbody></table></div>{economicRows.some(row=>asArray(row.scenarios).length>0)?<div className="table-wrap"><table><thead><tr><th>Ação / cenário</th><th>Preço terminal</th><th>Dividendos por ação · hipótese</th><th>Custos de saída · hipótese</th><th>Resultado líquido / retorno</th><th>Preço terminal de equilíbrio</th><th>Ganho da alternativa não escolhida</th></tr></thead><tbody>{economicRows.flatMap(row=>asArray(row.scenarios).map(asObject).map((scenario,index)=><tr key={asText(row.alternative_id)+':'+index}><td>{asText(row.ticker)} / {asText(scenario?.name)}</td><td>{brl(numberValue(scenario?.terminal_price_brl))}</td><td>{brl(numberValue(scenario?.user_gross_dividend_per_share_brl))??'UNKNOWN'}</td><td>{brl(numberValue(scenario?.user_exit_costs_brl))??'UNKNOWN'}</td><td>{brl(numberValue(scenario?.net_scenario_pnl_brl))??'UNKNOWN'} / {pct(numberValue(scenario?.net_scenario_return_fraction))??'UNKNOWN'}</td><td>{brl(numberValue(scenario?.breakeven_terminal_price_brl))??'UNKNOWN'}</td><td>{brl(numberValue(scenario?.opportunity_cost_brl))??'UNKNOWN'}</td></tr>))}</tbody></table></div>:<p className="muted">Você não informou preços futuros hipotéticos, dividendos e custos de saída; por isso esta comparação não projeta payoffs nem escolhe uma vencedora.</p>}<details><summary>Premissas da decisão</summary><ul>{asStrings(economic.limitations).map((item,index)=><li key={index}>{item}</li>)}</ul></details></section>}
    {stockPurchase&&<section className="analysis-section stock-pair-comparison">
      <h3>Compra entre ações · {stockPurchaseTickers.join(' × ') || 'ativos'} · comparação lado a lado</h3>
      <p>Dados observados até {when(asOf)}. O histórico mostra desempenho passado; não é previsão nem escolhe, sozinho, a melhor compra.</p>
      <h4>Desempenho histórico lado a lado</h4>
      <div className="table-wrap"><table aria-label="Desempenho histórico comparável das ações">
        <thead><tr><th>Período</th>{stockPurchaseTickers.map(ticker=><th key={ticker}>{ticker} · retorno observado</th>)}<th>Diferença entre ativos</th></tr></thead>
        <tbody>{['1W','1M','3M','6M','1Y'].map(period=>{
          const comparison=historicalComparisons.find(row=>asText(row.period)===period);
          const difference=numberValue(comparison?.right_minus_left_return_fraction);
          return <tr key={period}><th scope="row">{({'1W':'1 semana','1M':'1 mês','3M':'3 meses','6M':'6 meses','1Y':'1 ano'} as Record<string,string>)[period]}</th>
            {stockPurchaseTickers.map(ticker=>{
              const history=asObject(asObject(stockPurchaseByTicker.get(ticker)?.historical_returns)?.[period]);
              const observed=numberValue(history?.return_fraction);
              const status=asText(history?.status);
              return <td key={ticker}>{observed==null?(status==='INSUFFICIENT_HISTORY'?`Amostra insuficiente · ${numberValue(history?.available_observations)??0}/${numberValue(history?.sessions)??'—'} pregões`:'Indisponível'):<>{pct(observed)}<small>{when(history?.start_at)} a {when(history?.end_at)} · {asText(history?.price_basis)??'base de preço não informada'}</small></>}</td>;
            })}
            <td>{asText(comparison?.status)==='COMPARABLE'&&difference!=null?pct(difference):'Sem comparação: janelas ou datas diferentes'}</td>
          </tr>;
        })}</tbody>
      </table></div>
      <p className="muted">Diferença = retorno de {stockPurchaseTickers[1]??'B'} menos {stockPurchaseTickers[0]??'A'}, somente quando o backend confirma datas comuns.</p>
      <h4>Fundamentos reportados</h4>
      <p>{fundamentalComparisons.filter(row=>asText(row.status)==='COMPARABLE').length} de {fundamentalMetricNames.length} métricas têm unidade, período e data compatíveis. A tabela mostra os valores de cada ativo e sinaliza métricas excluídas pelo corte ou sem comparação equivalente.</p>
      {fundamentalMetricNames.length>0?<div className="table-wrap"><table aria-label="Fundamentos comparados lado a lado">
        <thead><tr><th>Métrica</th>{stockPurchaseTickers.map(ticker=><th key={ticker}>{ticker}</th>)}<th>Comparabilidade / período</th></tr></thead>
        <tbody>{fundamentalMetricNames.map(name=>{
          const comparison=fundamentalComparisons.find(row=>asText(row.metric)===name);
          const leftMetric=asObject(asObject(stockPurchaseByTicker.get(stockPurchaseTickers[0]??'')?.fundamental_metrics)?.[name]);
          const rightMetric=asObject(asObject(stockPurchaseByTicker.get(stockPurchaseTickers[1]??'')?.fundamental_metrics)?.[name]);
          const leftExcluded=asArray(stockPurchaseByTicker.get(stockPurchaseTickers[0]??'')?.excluded_metrics).map(asObject).find(item=>asText(item?.metric)===name);
          const rightExcluded=asArray(stockPurchaseByTicker.get(stockPurchaseTickers[1]??'')?.excluded_metrics).map(asObject).find(item=>asText(item?.metric)===name);
          const status=asText(comparison?.status);
          const periodText=(metric:Obj|null)=>metric?[asText(metric.report_date),asText(metric.period_type)].filter(Boolean).join(' · '):'';
          const cell=(metric:Obj|null,excluded:Obj|null)=>metric?<>{fundamentalDisplay(name,metric)}<small>{periodText(metric)}{asText(metric.quality_status)==='WARNING'?' · qualidade WARNING: disponibilidade histórica da fonte não comprovada':''}</small></>:excluded?<>{asText(excluded.reason)==='UNQUALIFIED_OR_FUTURE_FUNDAMENTAL'?'Excluída do corte':'Não qualificada'}<small>Data do registro: {asText(excluded.report_date)??'indisponível'} · não usada na comparação</small></>:'Sem dado elegível';
          return <tr key={name}><th scope="row">{fundamentalLabel(name)}</th><td>{cell(leftMetric,leftExcluded??null)}</td>{stockPurchaseTickers.length>1&&<td>{cell(rightMetric,rightExcluded??null)}</td>}<td>{status==='COMPARABLE'?'Comparável':status==='NONCOMPARABLE_OR_MISSING'?'Não comparável: falta dado equivalente ou período ou unidade não coincide':'Sem par comparável'}</td></tr>;
        })}</tbody>
      </table></div>:<p className="muted">Nenhuma métrica fundamental passou pelos critérios de data, unidade e qualidade neste corte.</p>}
      <h4>Risco histórico observado</h4>
      <div className="table-wrap"><table aria-label="Risco histórico por ativo"><thead><tr><th>Ativo</th><th>Volatilidade realizada · 60 pregões</th><th>Drawdown máximo observado</th></tr></thead>
        <tbody>{stockPurchaseTickers.map(ticker=>{const risk=asObject(stockPurchaseByTicker.get(ticker)?.observed_risk);return <tr key={ticker}><th scope="row">{ticker}</th><td>{pct(numberValue(risk?.volatility_60d))??'Indisponível'}</td><td>{pct(numberValue(risk?.max_drawdown))??'Indisponível'}</td></tr>;})}</tbody>
      </table></div>
      <p>Retorno futuro, probabilidade de valorização, dividendos futuros e preço-alvo qualificado: indisponíveis sem evidências específicas. A qualidade WARNING informa limites de proveniência; não significa por si só que o valor esteja incorreto.</p>
      <details><summary>Fontes, métricas excluídas e limitações</summary>
        <ul>{stockPurchaseRows.map(row=><li key={asText(row.ticker)}>{asText(row.ticker)} · fontes: {asStrings(row.source_refs).join(' · ')||'indisponíveis'}</li>)}
          {stockPurchaseRows.flatMap(row=>asArray(row.excluded_metrics).map(asObject).map((item,index)=><li key={`${asText(row.ticker)}:${asText(item?.metric)}:${index}`}>{asText(row.ticker)} · {fundamentalLabel(asText(item?.metric)??'Métrica')} · registro {asText(item?.report_date)??'sem data'} excluído do corte.</li>))}
          {asStrings(stockPurchase.limitations).map((item,index)=><li key={`limit:${index}`}>{item}</li>)}
        </ul>
      </details>
    </section>}
    {stockPurchase&&stockPurchaseRows.map(row=>{const dividends=asObject(row.dividends);return dividends&&<section className="analysis-section" key={'dividends:'+asText(row.alternative_id)}><h3>Dividendos e JCP · {asText(row.ticker)}</h3><p>Coleta: {asText(dividends.collection_status)} · cobertura da fonte não comprovada</p><p>Pagamentos observados em 365 dias por ação, bruto: {brl(numberValue(dividends.observed_paid_365d_gross_per_share_brl))??'UNKNOWN'} · Anunciados com data-com futura, condicionais: {brl(numberValue(dividends.announced_conditional_gross_per_share_brl))??'UNKNOWN'}</p><div className="table-wrap"><table><thead><tr><th>Tipo / valor bruto por ação</th><th>Anúncio</th><th>Data-com / ex</th><th>Pagamento</th><th>Elegibilidade de nova compra</th><th>Fonte / qualidade</th></tr></thead><tbody>{asArray(dividends.events).map(asObject).map((event,index)=><tr key={index}><td>{asText(event?.payment_type)} / {brl(numberValue(event?.gross_amount_per_share_brl))??'UNKNOWN'}</td><td>{asText(event?.announcement_date)??'UNKNOWN'}</td><td>{asText(event?.record_date)??'UNKNOWN'} / {asText(event?.ex_date)??'UNKNOWN'}</td><td>{asText(event?.payment_date)??'UNKNOWN'}<small>{asText(event?.payment_status)}</small></td><td>{event?.new_purchase_entitlement==='EXCLUDED_FOR_NEW_PURCHASE'?'Data-com passada · excluído para nova compra':event?.new_purchase_entitlement==='CONDITIONAL_FUTURE_RECORD_DATE'?'Condicional · data-com futura':'UNKNOWN'}</td><td>{asText(event?.source)} · {asText(event?.quality_status)}<small>{asText(event?.source_record_id)}</small></td></tr>)}</tbody></table></div><details><summary>Premissas e exclusões</summary><ul>{asStrings(dividends.limitations).map((item,index)=><li key={index}>{item}</li>)}{asArray(dividends.exclusions).map(asObject).map((item,index)=><li key={'excluded:'+index}>{asText(item?.source_record_id)} · {asText(item?.reason)}</li>)}</ul></details></section>;})}
    {stockPurchase&&stockPurchaseRows.map(row=>{const targets=asObject(row.institution_targets);return targets&&<section className="analysis-section" key={'targets:'+asText(row.alternative_id)}><h3>Preços-alvo institucionais · {asText(row.ticker)}</h3><p>{asText(targets.status)} · opiniões das instituições, sem consenso ou retorno esperado inferido</p><div className="table-wrap"><table><thead><tr><th>Instituição</th><th>Preço-alvo</th><th>Publicação</th><th>Horizonte</th><th>Fonte</th></tr></thead><tbody>{asArray(targets.rows).map(asObject).map((target,index)=><tr key={index}><td>{asText(target?.institution)}</td><td>{brl(numberValue(target?.price_brl))}</td><td>{when(target?.published_at)}</td><td>{asText(target?.horizon_date)}</td><td>{asText(target?.source_url)}<small>{asText(target?.document_id)}</small></td></tr>)}</tbody></table></div><ul>{asStrings(targets.limitations).map((item,index)=><li key={index}>{item}</li>)}</ul></section>;})}
    {putPair&&<section className="analysis-section"><h3>Duas PUTs · prêmio, risco e prazo</h3><p>{putPair.ranking==='NOT_REQUESTED'?'Comparação sem vencedor':putPair.ranking==='TIE'?'Empate no objetivo informado':putPair.ranking==='UNKNOWN_OBJECTIVE_INPUTS'?'Dados insuficientes para ordenar':'Ordem condicionada ao objetivo informado'} · {putPair.objective==='LOWEST_MODEL_EXPIRY_ITM'?'menor estimativa de ITM no próprio vencimento':putPair.objective==='HIGHEST_GROSS_PREMIUM_PER_CAPITAL_30D'?'maior prêmio bruto por capital normalizado a 30 dias':'prêmio, risco e prazo'}</p>{putPair.different_expiries===true&&<p className="muted">Vencimentos distintos: riscos cobrem prazos diferentes. Os cenários terminais não definem um vencedor comum.</p>}<div className="table-wrap"><table><thead><tr><th>Ordem condicional</th><th>Contrato</th><th>Vencimento / dias</th><th>Bid / ask · volume / OI</th><th>Prêmio bruto</th><th>Capital</th><th>Ação / strike / break-even</th><th>Margem até strike / break-even</th><th>Perda máxima pré-custos</th><th>Prêmio/capital · 30 dias</th><th>ITM / toque · modelo</th><th>Exercício antecipado</th></tr></thead><tbody>{putPairRows.map(row=><tr key={asText(row.option_id)}><td>{numberValue(row.rank)??'—'}</td><td>{asText(row.option_id)} · {asText(row.underlying_ticker)}</td><td>{asText(row.expiration_date)} / {numberValue(row.days_to_expiration)}</td><td>{brl(numberValue(row.bid))} / {brl(numberValue(row.ask))??'UNKNOWN'} · {numberValue(row.volume)??'UNKNOWN'} / {numberValue(row.open_interest)??'UNKNOWN'}<small>{when(row.quote_observed_at)}</small></td><td>{brl(numberValue(row.premium_total_one_contract_brl))}</td><td>{brl(numberValue(row.capital_required_one_contract_brl))}</td><td>{brl(numberValue(row.underlying_price))??'UNKNOWN'} / {brl(numberValue(row.strike))} / {brl(numberValue(row.breakeven_price))}</td><td>{pct(numberValue(row.downside_to_strike_fraction))??'UNKNOWN'} / {pct(numberValue(row.breakeven_cushion_fraction))??'UNKNOWN'}</td><td>{brl(numberValue(row.maximum_loss_one_contract_before_costs_brl))}</td><td>{numberValue(row.gross_premium_per_capital_30d_pct)?.toFixed(3)}%</td><td>{numberValue(row.expiry_itm_probability)===null?'UNKNOWN':pct(numberValue(row.expiry_itm_probability))} / {numberValue(row.touch_probability)===null?'UNKNOWN':pct(numberValue(row.touch_probability))}</td><td>{row.exercise_style==='EUROPEAN'?'Europeia, conforme provedor':'UNKNOWN · estilo americano ou não informado'}</td></tr>)}</tbody></table></div><p className="muted">Estimativas não calibradas; custos e retorno líquido esperado permanecem UNKNOWN.</p><details><summary>Premissas e limitações</summary><ul>{asStrings(putPair.limitations).map((item,index)=><li key={index}>{item}</li>)}</ul></details></section>}
    {fundedSwitch&&<section><h3>Troca financiada · {asText(fundedSwitch.sell_ticker)} → {asText(fundedSwitch.buy_ticker)}</h3><p>Modelo pelo preço de referência; ordens não executadas. {asText(fundedSwitch.status)}</p><div className="table-wrap"><table><tbody>{[['Quantidade vendida','sell_quantity'],['Quantidade comprável','buy_quantity'],['Quantidade restante na origem','remaining_source_stock_quantity']].map(([label,key])=><tr key={key}><th>{label}</th><td>{numberValue(fundedSwitch[key])??'UNKNOWN'}</td></tr>)}{[['Venda bruta','gross_sale_proceeds_brl'],['Custos informados','fees_brl'],['Impostos informados','taxes_brl'],['Venda líquida','net_sale_proceeds_brl'],['Compra modelada','purchase_notional_brl'],['Caixa residual','residual_cash_brl']].map(([label,key])=><tr key={key}><th>{label}</th><td>{numberValue(fundedSwitch[key])===null?'UNKNOWN':brl(numberValue(fundedSwitch[key]))}</td></tr>)}</tbody></table></div>{fundedSwitch.related_option_positions_present===true&&<p className="muted">Há opções relacionadas: a troca pode alterar cobertura ou garantias e exige análise específica.</p>}</section>}

    {proposal && <section className="analysis-section">
      <h4>Decisão proposta · revisão humana</h4>
      <dl>
        <div><dt>Ação / alternativa</dt><dd>{asText(proposal.action) ?? 'UNKNOWN'} · {asText(proposal.subject_id) ?? 'UNKNOWN'}</dd></div>
        <div><dt>Confiança declarada pelo agente</dt><dd>{asText(proposal.confidence) ?? 'UNKNOWN'}</dd></div>
        <div><dt>Impacto no capital</dt><dd>{asText(proposal.capital_impact) ?? 'Indisponível'}</dd></div>
        <div><dt>Custo de oportunidade</dt><dd>{asText(proposal.opportunity_cost) ?? 'Indisponível'}</dd></div>
      </dl>
      <BulletSection title="O que invalidaria esta decisão" values={asStrings(proposal.invalidation_conditions)} />
      <BulletSection title="Referências da decisão" values={asStrings(proposal.evidence_refs)} />
      {asObject(result.risk_validation) && <>
        <p>Validação determinística: {asText(asObject(result.risk_validation)?.status) ?? 'UNKNOWN'}</p>
        <BulletSection title="Motivos da validação" values={asStrings(asObject(result.risk_validation)?.reasons)} />
      </>}
    </section>}

    {asArray(proposal?.alternative_assessments).length > 0 && <section className="analysis-section">
      <h4>Análise por alternativa · interpretação dos agentes</h4>
      <div className="evidence-grid">{asArray(proposal?.alternative_assessments).map((value, index) => {
        const assessment = asObject(value);
        return <article className="evidence-card" key={asText(assessment?.alternative_id) ?? String(index)}>
          <h5>{asText(assessment?.alternative_id) ?? 'Alternativa'}</h5>
          <BulletSection title="Evidências favoráveis" values={asStrings(assessment?.supporting_evidence)} />
          <BulletSection title="Evidências contrárias" values={asStrings(assessment?.contradicting_evidence)} />
          <BulletSection title="Implicações para a decisão" values={asStrings(assessment?.decision_implications)} />
          <BulletSection title="O que falta saber" values={asStrings(assessment?.unknowns)} />
          <BulletSection title="Referências" values={asStrings(assessment?.evidence_refs)} />
        </article>;
      })}</div>
    </section>}

    {rationale && <section className="analysis-section"><h4>Racional</h4><p>{rationale}</p></section>}
    {workspaceName === 'Opportunities' && !opportunityScreen && rankedOpportunities.length === 0 && <div className="state-banner limited">
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

    {workspaceIntelligence && <details className="analysis-section"><summary>Contexto integrado e evidências dos agentes</summary>
      <h4>Inteligência integrada</h4>
      <p className="muted">
        Fatos numéricos permanecem sob autoridade dos serviços B3. DeepSeek, João Resolve e os agentes senior interpretam as evidências sem substituir esses fatos.
      </p>
      <div className="evidence-grid">
        {marketAgent && <article className="evidence-card">
          <h5>Agente B3 · Mercado</h5>
          <p>{asText(marketAgent.summary) ?? 'Sem síntese disponível.'}</p>
          <BulletSection title="Achados e implicações" values={asStrings(marketAgent.findings)} />
          <BulletSection title="Riscos identificados" values={asStrings(marketAgent.risks)} />
          <BulletSection title="Evidências e fontes" values={[...asStrings(marketAgent.evidence_refs), ...asStrings(marketAgent.source_refs)]} />
        </article>}
        {portfolioAgent && <article className="evidence-card">
          <h5>Agente B3 · Portfólio</h5>
          <p>{asText(portfolioAgent.summary) ?? 'Sem síntese disponível.'}</p>
          <BulletSection title="Achados e implicações" values={asStrings(portfolioAgent.findings)} />
          <BulletSection title="Riscos identificados" values={asStrings(portfolioAgent.risks)} />
          <BulletSection title="Evidências e fontes" values={[...asStrings(portfolioAgent.evidence_refs), ...asStrings(portfolioAgent.source_refs)]} />
        </article>}
        {optionsAgent && <article className="evidence-card">
          <h5>Agente B3 · Opções</h5>
          <p>{asText(optionsAgent.summary) ?? 'Sem síntese disponível.'}</p>
          <BulletSection title="Achados e implicações" values={asStrings(optionsAgent.findings)} />
          <BulletSection title="Riscos identificados" values={asStrings(optionsAgent.risks)} />
          <BulletSection title="Evidências e fontes" values={[...asStrings(optionsAgent.evidence_refs), ...asStrings(optionsAgent.source_refs)]} />
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
        <summary>Enriquecimento assíncrono · inteligência B3 por ativo</summary>
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
    </details>}

    {positions.length > 0 && <section className="analysis-section">
      <h4>Carteira considerada</h4>
      <p>{positions.length} posições no snapshot{asOf ? ` de ${asOf}` : ''}. A síntese deve considerar essa exposição; divergências entre fontes aparecem em Conflitos.</p>
      {(assignmentCapital != null || uncoveredCallShares != null) && <p>
        {assignmentCapital != null ? `Capital potencial de exercício/assign: ${brl(assignmentCapital)}.` : ''}
        {uncoveredCallShares != null ? ` Ações descobertas em calls: ${uncoveredCallShares}.` : ''}
      </p>}
    </section>}

      {opportunityScreen && <section className="analysis-section">
      <h4>Comparação de ações · risco e liquidez observados</h4>
      <p>{screenStatus[asText(opportunityScreen.status) ?? ''] ?? 'Estado indisponível'}</p>
      <p className="muted">Objetivo: {asText(opportunityScreen.objective) === 'LOWEST_REALIZED_VOLATILITY_60D' ? 'menor volatilidade realizada em 60 retornos' : asText(opportunityScreen.objective) === 'HIGHEST_OBSERVED_LIQUIDITY_20D' ? 'maior proxy de liquidez em 20 observações' : 'comparar sem ordenar'}.
        {' '}Janela comparável: {asText(opportunityScreen.reference_window_start) ?? 'Indisponível'} a {asText(opportunityScreen.reference_window_end) ?? 'Indisponível'}.
        {' '}Ordenação calculada pelo backend; não representa maior retorno futuro ou recomendação de compra.</p>
      <div className="table-wrap"><table><thead><tr><th>Posição no objetivo</th><th>Ativo</th><th>Carteira</th><th>Qtd. de ações</th><th>Cotação atual</th><th>Data da cotação</th><th>Volatilidade realizada 60d</th><th>Proxy de liquidez média 20d</th><th>Cobertura / exclusões</th></tr></thead><tbody>{screenedRows.map(row => {
        const holding = asObject(row.portfolio);
        return <tr key={asText(row.ticker)}>
          <td>{numberValue(row.rank) ?? 'Sem ranking'}</td><td>{asText(row.ticker)}</td>
          <td>{holding?.held === true ? 'Dentro' : holding?.held === false ? 'Fora' : 'UNKNOWN'}</td>
          <td>{numberValue(holding?.stock_quantity)?.toLocaleString('pt-BR') ?? 'Indisponível'}</td>
          <td>{brl(numberValue(row.current_price)) ?? 'Indisponível'}</td><td>{when(row.quote_as_of)}</td>
          <td>{pct(numberValue(row.volatility_60d)) ?? 'Indisponível'}</td><td>{brl(numberValue(row.liquidity_proxy_20d)) ?? 'Indisponível'}</td>
          <td>{numberValue(row.history_count) ?? 0} observações{asStrings(row.exclusions).map(reason => <p className="muted" key={reason}>{screeningReasons[reason] ?? reason}</p>)}</td>
        </tr>;
      })}</tbody></table></div>
      <p className="muted">Liquidez aproximada: fechamento ajustado quando disponível (senão fechamento) × volume; não é o volume financeiro efetivamente negociado. Empates ficam na mesma posição. Preço-alvo e retorno esperado: UNKNOWN nesta política.</p>
      <BulletSection title="Premissas e limites da ordenação" values={asStrings(opportunityScreen.limitations)} />
      <details><summary>Fontes por ativo e evidência do cálculo</summary>{screenedRows.map(row => <p key={asText(row.ticker)}>{asText(row.ticker)} · {asStrings(row.source_refs).join(' · ')} · {asText(row.ranking_evidence_ref)}</p>)}</details>
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
                    <div><dt>Capital incremental</dt><dd>{brl(incrementalCapital) ?? 'Indisponível'}</dd></div>
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
      <div className="table-wrap"><table aria-label="Comparação de alternativas lado a lado">
        <thead><tr><th>Métrica</th>{strategyAlternatives.map((item,index)=><th key={asText(item.alternative_id)??String(index)}>{asText(item.subject_id)??'Ativo'} · {asText(item.label)??asText(item.action_type)??'Alternativa'}</th>)}</tr></thead>
        <tbody>
          {strategyMetrics.map(row=><tr key={row.key}><th scope="row">{row.label}</th>{strategyAlternatives.map((item,index)=><td key={asText(item.alternative_id)??String(index)}>{row.format(numberValue(item[row.key]))??'Indisponível'}</td>)}</tr>)}
          <tr><th scope="row">Data de referência</th>{strategyAlternatives.map((item,index)=><td key={index}>{when(item.as_of)}</td>)}</tr>
          <tr><th scope="row">Qualidade</th>{strategyAlternatives.map((item,index)=><td key={index}>{asText(item.quality_status)??'Indisponível'}</td>)}</tr>
          <tr><th scope="row">Fontes</th>{strategyAlternatives.map((item,index)=><td key={index}>{asStrings(item.source_refs).join(' · ')||'Indisponível'}</td>)}</tr>
        </tbody>
      </table></div>
      <p className="muted">Valores fornecidos pelo backend. Indisponível não significa zero; esta tabela não escolhe um vencedor.</p>
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
      <Suspense fallback={<State kind="loading" title="Carregando cenários">Preparando a comparação visual.</State>}><ScenarioChart value={scenarioAnalysis}/></Suspense>
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
    <BulletSection title="Conflitos entre análises" values={asStrings(synthesis?.conflicts)} />
    <BulletSection title="Riscos" values={risks} />
    <BulletSection title="Incertezas" values={uncertainties} />
    <BulletSection title="Lacunas de evidência" values={evidenceGaps} />
    <BulletSection title="Limitações" values={limitations} />

    {data.sources?.length > 0 && <details className="analysis-sources">
      <summary>Fontes ({data.sources.length})</summary>
      {data.sources.map((source, index) => <p key={index}>{source}</p>)}
    </details>}


  </div>;
}
