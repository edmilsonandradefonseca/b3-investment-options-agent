export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export type JsonObject = { [key: string]: JsonValue };

export type ApiErrorPayload = {
  detail?: string;
  error?: string | null;
};

export type HealthResponse = {
  status: string;
  service: string;
  workflow_configured: boolean;
  llm_enabled: boolean;
  runtime: {
    embedding_url: string;
    qdrant_url: string;
    neo4j_uri: string;
    qdrant_collection: string;
    oplab_token_configured: boolean;
    brapi_token_configured: boolean;
  };
};

export type VersionResponse = {
  service: string;
  version: string;
};

export type OrchestrateRequest = {
  task: string;
  ticker?: string | null;
  context?: Record<string, unknown>;
};

export type OrchestrateResponse = {
  status: string;
  result: Record<string, unknown>;
  sources: string[];
  audit: Array<Record<string, unknown>>;
  error: string | null;
};

export type TransactionRequest = {
  action: string;
  instrument_type: string;
  ticker: string;
  quantity: number;
  price: number;
  executed_at?: string | null;
  broker?: string;
};

export type TransactionResponse = {
  transaction_id: string;
  executed_at: string;
  action: string;
  instrument_type: string;
  ticker: string;
  quantity: number;
  price: number;
  broker: string;
  source_ref: string;
};

export type SnapshotImportResponse = {
  status: string;
  file: string;
  active_file: string;
  message: string;
};

export type BrokerageNoteImportResponse = {
  status: string;
  file: string;
  active_file: string;
  note_number: string | null;
  trade_date: string | null;
  parsed_count: number;
  inserted_count: number;
  transaction_ids: string[];
  message: string;
};

export type BrokerageBatchImportResponse = Record<string, unknown>;

export type PortfolioPosition = {
  position_id: string; ticker: string; instrument_type: "STOCK" | "OPTION";
  quantity: number; average_cost: number | null; market_price: number | null;
  market_value: number | null; underlying_ticker: string | null;
  option_type: string | null; strike: number | null; expiration_date: string | null;
  source_ref: string;
};
export type PortfolioSnapshot = {
  status: string; as_of: string | null; updated_at: string | null;
  source_refs?: string[]; positions: PortfolioPosition[]; intelligence?: Record<string, unknown>;
  received_income?: {
    period_start: string; period_end: string; coverage: string; source_ref: string;
    duplicate_rows_omitted: number;
    summaries: Array<{ticker: string; dividends_net: number | null; jcp_net: number | null; total_net: number | null; payment_count: number}>;
    payments: Array<{ticker: string; payment_date: string; payment_type: string; quantity: number | null; gross_amount: number | null; net_amount: number | null; source_ref: string}>;
  } | null;
};
export type CapitalProfile = {
  status: string; account: string; available_capital: number | null;
  minimum_reserve: number | null; usable_capital: number | null; updated_at: string | null;
};

export type BrokerageOperation = {
  transaction_id: string; instrument_type?: "STOCK" | "OPTION"; option_ticker: string; side: "BUY" | "SELL";
  quantity: number; execution_price: number | null; cash_flow: number | null;
  trade_date: string | null; broker: string; note_number: string | null; source_ref: string;
};
export type BrokerageLedger = { status: string; operations: BrokerageOperation[] };
export type PilotAnalysis = {
  ticker: string; status: string;
  evidence?: { collected_at: string; source_refs: string[]; news: Array<{headline: string; published_date: string; source_ref: string}>; latest_market_record?: {close: number; observation_timestamp: string; source: string}; news_error?: string | null };
  deepseek_status?: string; deepseek?: {model: string; analysis: string};
  openclaw_status?: string; openclaw?: {model: string; analysis: {summary: string; risks: string[]; catalysts: string[]; limitations: string[]; evidence_refs: string[]}};
  deepseek_error?: string; openclaw_error?: string;
};

export type DataRecord = {
  instrument_id: string;
  ticker: string;
  observation_timestamp: string;
  available_timestamp: string;
  source: string;
  ingested_at: string;
  source_record_id: string;
};

export type StockMarketData = DataRecord & {
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close: number | null;
  vwap: number | null;
  currency: string;
};

export type OptionContract = {
  option_id: string;
  underlying_id: string;
  underlying_ticker: string;
  option_ticker: string;
  option_type: string;
  strike: number;
  expiration_date: string;
  exercise_style: string | null;
  contract_multiplier: number;
  currency: string;
};

export type OptionQuote = DataRecord & {
  option_id: string;
  bid: number | null;
  ask: number | null;
  last: number | null;
  mid: number | null;
  volume: number;
  open_interest: number | null;
  implied_volatility: number | null;
  delta: number | null;
  gamma: number | null;
  theta: number | null;
  vega: number | null;
  rho: number | null;
};

export type OptionsAnalysis = {
  puts: Array<Record<string, unknown>>;
  calls: Array<Record<string, unknown>>;
  source_refs: string[];
  quality_status: "VALIDATED" | "WARNING" | "REJECTED";
  assumptions: Record<string, unknown> | null;
};

export type LiveAnalysisResponse = {
  ticker: string;
  as_of: string;
  source_refs: string[];
  market: {
    history_count: number;
    price_history?: StockMarketData[];
    quant?: Record<string, unknown> | null;
    current_quote: StockMarketData | null;
    current_quote_status: "AVAILABLE" | "UNAVAILABLE";
    history_latest: StockMarketData;
    latest: StockMarketData;
  };
  options: {
    contract_count: number;
    quote_count: number;
    contracts: OptionContract[];
    quotes: OptionQuote[];
    analysis: OptionsAnalysis;
  };
};

export type FundamentalMetric = {
  ticker: string;
  metric: string;
  value: number;
  unit: string | null;
  source: string;
  source_record_id: string | null;
  observation_timestamp: string;
  available_timestamp: string;
  report_date: string | null;
  period_type: string | null;
  quality_status: string;
  quality_flags: string[];
};

export type FundamentalsResponse = {
  ticker: string;
  as_of: string;
  status: "AVAILABLE" | "NO_DATA";
  metrics: FundamentalMetric[];
  source_refs: string[];
  excluded_future_count: number;
  limitations: string[];
};

export type ResearchNewsResponse = {
  ticker: string;
  as_of: string;
  excluded_future_count?: number;
  source_refs: string[];
  events: Array<Record<string, unknown>>;
};


export type CurrentMarketQuoteResponse = {
  ticker: string;
  as_of: string;
  source: string;
  quote: StockMarketData;
};

export type CurrentOptionRow = {
  contract: OptionContract;
  quote: OptionQuote;
};

export type CurrentOptionsResponse = {
  ticker: string;
  as_of: string;
  source: string;
  option_type: "PUT" | "CALL" | null;
  count: number;
  options: CurrentOptionRow[];
};


export type RuntimeStatusResponse = {
  runtime: string;
  runtime_root: string;
  health: string;
  api: { host: string; port: number; local_health_url: string };
  resources: Record<string, string>;
  services: Record<string, { state: string; ownership?: string; endpoint?: string }>;
  scheduler?: { state: string; timers: Array<{ unit: string; activates: string | null; next: string | null; last: string | null }> };
  process: {
    running: boolean;
    runtime_pid?: number | null;
    runtime_pid_running?: boolean;
    orchestrator_pid?: number | null;
    orchestrator_pid_running?: boolean;
  };
};

export type SchedulerConfigResponse = {
  start_time: string;
  end_time: string;
  interval_minutes: 15 | 30 | 60;
  timezone: string;
  weekdays: string[];
  source: "admin" | "environment";
};

export type CollectionUniverseResponse = {
  configured_tickers: string[];
  portfolio_tickers: string[];
  effective_tickers: string[];
  updated_at: string | null;
  source: "admin" | "environment" | "default";
};


export type InvestorFlowObservation = {
  investor_type: string;
  market_segment: string;
  net_financial_value: number | null;
  observation_date: string | null;
  observation_timestamp: string;
  source: string;
  source_record_id: string | null;
  quality_status: string;
  quality_flags: string[];
};

export type InvestorFlowResponse = {
  status: "OK" | "NO_DATA";
  source: string;
  as_of: string;
  unit: "NOT_DECLARED_BY_PROVIDER";
  observations: InvestorFlowObservation[];
};

export type YieldCurveObservation = {
  curve_code: string;
  curve_description: string;
  days_calendar: number;
  days_business: number;
  rate_decimal: number;
  rate_percent_per_year: number;
  vertex: string;
  observation_timestamp: string;
  source_record_id: string | null;
  quality_status: string;
};

export type YieldCurveResponse = {
  status: "OK" | "NO_DATA";
  source: string;
  curve: string;
  curve_description: string;
  as_of: string | null;
  unit: "percent_per_year";
  observations: YieldCurveObservation[];
};
