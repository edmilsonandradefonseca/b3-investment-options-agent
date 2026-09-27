import type {
  ApiErrorPayload,
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

export const API_BASE_URL =
  (import.meta.env.VITE_B3_API_URL as string | undefined) ??
  (import.meta.env.VITE_ORCHESTRATOR_URL as string | undefined) ??
  DEFAULT_API_BASE_URL;

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
  return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
}

async function readError(response: Response): Promise<ApiErrorPayload | null> {
  try {
    return (await response.json()) as ApiErrorPayload;
  } catch {
    return null;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), init);
  if (!response.ok) {
    const payload = await readError(response);
    throw new ApiError(
      payload?.detail ?? payload?.error ?? `HTTP ${response.status}`,
      response.status,
      payload,
    );
  }
  return (await response.json()) as T;
}

async function upload<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  return requestJson<T>(path, { method: "POST", body });
}

export const b3Api = {
  health: () => requestJson<HealthResponse>("/health"),
  version: () => requestJson<VersionResponse>("/version"),

  orchestrate: (request: OrchestrateRequest) =>
    requestJson<OrchestrateResponse>("/orchestrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),

  listTransactions: (limit = 100) =>
    requestJson<TransactionResponse[]>(`/transactions?limit=${encodeURIComponent(limit)}`),

  addTransaction: (request: TransactionRequest) =>
    requestJson<TransactionResponse>("/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    }),

  importPortfolio: (file: File) =>
    upload<SnapshotImportResponse>("/imports/portfolio", file),

  importOptions: (file: File) =>
    upload<SnapshotImportResponse>("/imports/options", file),

  importBrokerageNote: (file: File) =>
    upload<BrokerageNoteImportResponse>("/imports/brokerage-notes", file),

  importBrokerageBatch: (file: File) =>
    upload<BrokerageBatchImportResponse>("/imports/brokerage-notes/batch", file),

  brokerageBatchUploadUrl: () => apiUrl("/imports/brokerage-notes/upload"),

  liveAnalysis: (ticker: string) =>
    requestJson<LiveAnalysisResponse>(
      `/analysis/live/${encodeURIComponent(ticker.trim().toUpperCase())}`,
    ),

  researchNews: (ticker: string, limit = 20) =>
    requestJson<ResearchNewsResponse>(
      `/research/news/${encodeURIComponent(ticker.trim().toUpperCase())}?limit=${encodeURIComponent(limit)}`,
    ),
};
