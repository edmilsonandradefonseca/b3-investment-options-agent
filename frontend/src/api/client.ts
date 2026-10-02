import type {
  ApiErrorPayload,
  CapitalProfile,
  BrokerageLedger,
  CurrentMarketQuoteResponse,
  CurrentOptionsResponse,
  PilotAnalysis,
  PortfolioSnapshot,
  BrokerageBatchImportResponse,
  BrokerageNoteImportResponse,
  HealthResponse,
  LiveAnalysisResponse,
  OrchestrateRequest,
  OrchestrateResponse,
  ResearchNewsResponse,
  SnapshotImportResponse,
  TransactionRequest,
  TransactionResponse,
  VersionResponse,
} from "./contracts";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const STORAGE_KEY = "b3.apiBaseUrl";

function envBaseUrl(): string | undefined {
  return (
    (import.meta.env.VITE_B3_API_URL as string | undefined) ??
    (import.meta.env.VITE_ORCHESTRATOR_URL as string | undefined)
  );
}

export function getApiBaseUrl(): string {
  const stored = typeof window !== "undefined" ? window.localStorage.getItem(STORAGE_KEY) : null;
  return (stored || envBaseUrl() || DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

export function setApiBaseUrl(value: string): string {
  const normalized = value.trim().replace(/\/$/, "");
  if (!/^https?:\/\//i.test(normalized)) {
    throw new Error("Backend URL must start with http:// or https://");
  }
  window.localStorage.setItem(STORAGE_KEY, normalized);
  return normalized;
}

export function resetApiBaseUrl(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

export class ApiError extends Error {
  readonly status: number;
  readonly payload: ApiErrorPayload | null;

  constructor(message: string, status: number, payload: ApiErrorPayload | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function apiUrl(path: string): string {
  return `${getApiBaseUrl()}${path}`;
}

async function readError(response: Response): Promise<ApiErrorPayload | null> {
  try {
    return (await response.json()) as ApiErrorPayload;
  } catch {
    return null;
  }
}

async function requestJson<T>(path: string, init?: RequestInit, timeoutMs = 30_000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(apiUrl(path), { ...init, signal: controller.signal });
    if (!response.ok) {
      const payload = await readError(response);
      throw new ApiError(
        payload?.detail ?? payload?.error ?? `HTTP ${response.status}`,
        response.status,
        payload,
      );
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`Tempo limite excedido ao aguardar o backend (${Math.round(timeoutMs / 1000)}s).`);
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

async function upload<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  return requestJson<T>(path, { method: "POST", body });
}

export const b3Api = {
  personalHistory: (ticker: string) => requestJson<Record<string, unknown>>(`/history/context?ticker=${encodeURIComponent(ticker.trim().toUpperCase())}`),
  health: () => requestJson<HealthResponse>("/health"),
  portfolio: () => requestJson<PortfolioSnapshot>("/portfolio/current"),
  optionLedger: () => requestJson<BrokerageLedger>("/options/ledger"),
  pilotAnalysis: (ticker: string) => requestJson<PilotAnalysis>(`/intelligence/pilot/${encodeURIComponent(ticker.trim().toUpperCase())}`),
  capital: () => requestJson<CapitalProfile>("/capital-profile"),
  saveCapital: (available_capital: number, minimum_reserve: number) => requestJson<CapitalProfile>("/capital-profile", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ available_capital, minimum_reserve }),
  }),
  version: () => requestJson<VersionResponse>("/version"),
  orchestrate: (request: OrchestrateRequest) =>
    requestJson<OrchestrateResponse>("/orchestrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }, 195_000),
  listTransactions: (limit = 100) =>
    requestJson<TransactionResponse[]>(`/transactions?limit=${encodeURIComponent(limit)}`),
  addTransaction: (request: TransactionRequest) =>
    requestJson<TransactionResponse>("/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),
  importPortfolio: (file: File) => upload<SnapshotImportResponse>("/imports/portfolio", file),
  importOptions: (file: File) => upload<SnapshotImportResponse>("/imports/options", file),
  importBrokerageNote: (file: File) => upload<BrokerageNoteImportResponse>("/imports/brokerage-notes", file),
  importBrokerageBatch: (file: File) => upload<BrokerageBatchImportResponse>("/imports/brokerage-notes/batch", file),
  brokerageBatchUploadUrl: () => apiUrl("/imports/brokerage-notes/upload"),
  currentMarketQuote: (ticker: string) =>
    requestJson<CurrentMarketQuoteResponse>(
      `/market/current/${encodeURIComponent(ticker.trim().toUpperCase())}`,
    ),
  currentOptions: (ticker: string, optionType: "PUT" | "CALL" = "PUT", limit = 100) =>
    requestJson<CurrentOptionsResponse>(
      `/options/current/${encodeURIComponent(ticker.trim().toUpperCase())}?option_type=${encodeURIComponent(optionType)}&limit=${encodeURIComponent(limit)}`,
    ),
  liveAnalysis: (ticker: string) =>
    requestJson<LiveAnalysisResponse>(`/analysis/live/${encodeURIComponent(ticker.trim().toUpperCase())}`),
  researchNews: (ticker: string, limit = 20) =>
    requestJson<ResearchNewsResponse>(
      `/research/news/${encodeURIComponent(ticker.trim().toUpperCase())}?limit=${encodeURIComponent(limit)}`,
    ),
};
