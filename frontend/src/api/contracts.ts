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
  source_refs?: string[]; positions: PortfolioPosition[];
};
export type CapitalProfile = {
  status: string; account: string; available_capital: number | null;
  minimum_reserve: number | null; usable_capital: number | null; updated_at: string | null;
};

export type BrokerageOperation = {
  transaction_id: string; option_ticker: string; side: "BUY" | "SELL";
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
    current_quote: StockMarketData | null;
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

export type ResearchNewsResponse = {
  ticker: string;
  as_of: string;
  excluded_future_count: number;
  source_refs: string[];
  events: Array<Record<string, unknown>>;
};
