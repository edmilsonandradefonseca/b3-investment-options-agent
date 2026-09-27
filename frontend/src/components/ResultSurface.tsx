import type { OrchestrateResponse } from "../api/contracts";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function scalar(value: unknown): string {
  if (value === null || value === undefined || value === "") return "UNKNOWN";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  return String(value);
}

function collectMetadata(value: unknown, depth = 0): UnknownRecord {
  if (depth > 4 || value === null || value === undefined) return {};
  if (Array.isArray(value)) {
    for (const item of value) {
      const found = collectMetadata(item, depth + 1);
      if (Object.keys(found).length) return found;
    }
    return {};
  }
  if (!isRecord(value)) return {};
  const out: UnknownRecord = {};
  for (const key of ["as_of", "quality_status", "quality", "status", "source_refs", "sources"]) {
    if (key in value) out[key] = value[key];
  }
  if (Object.keys(out).length) return out;
  for (const child of Object.values(value)) {
    const found = collectMetadata(child, depth + 1);
    if (Object.keys(found).length) return found;
  }
  return {};
}

function hasLimited(value: unknown): boolean {
  try {
    return JSON.stringify(value).toUpperCase().includes("LIMITED");
  } catch {
    return false;
  }
}

function ArrayTable({ rows }: { rows: UnknownRecord[] }) {
  const columns = Array.from(
    new Set(rows.slice(0, 20).flatMap((row) => Object.keys(row))),
  ).slice(0, 9);

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>{columns.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, 100).map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>
                  {isRecord(row[column]) || Array.isArray(row[column])
                    ? JSON.stringify(row[column])
                    : scalar(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > 100 && <small className="muted">Showing first 100 of {rows.length} rows.</small>}
    </div>
  );
}

function ValueView({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (depth > 3) return <pre className="inline-json">{JSON.stringify(value, null, 2)}</pre>;
  if (Array.isArray(value)) {
    if (!value.length) return <span className="unknown-value">No canonical data</span>;
    if (value.every(isRecord)) return <ArrayTable rows={value as UnknownRecord[]} />;
    return <div className="chip-list">{value.map((item, index) => <span key={index}>{scalar(item)}</span>)}</div>;
  }
  if (isRecord(value)) {
    return (
      <div className="structured-grid">
        {Object.entries(value).map(([key, child]) => (
          <section className="structured-field" key={key}>
            <label>{key.replaceAll("_", " ")}</label>
            <ValueView value={child} depth={depth + 1} />
          </section>
        ))}
      </div>
    );
  }
  return <strong className={value === null || value === undefined ? "unknown-value" : ""}>{scalar(value)}</strong>;
}

export function ResultSurface({ response }: { response: OrchestrateResponse | null }) {
  if (!response) {
    return (
      <div className="empty-state compact-empty">
        <div className="empty-icon">◇</div>
        <h3>Ready for real runtime data</h3>
        <p>Run the workspace analysis. The application will render only what the frozen backend returns.</p>
      </div>
    );
  }

  if (response.error) {
    return <div className="state-banner error"><strong>Backend error</strong><span>{response.error}</span></div>;
  }

  const metadata = collectMetadata(response.result);
  const limited = hasLimited(response.result) || response.status.toUpperCase().includes("LIMITED");

  return (
    <div className="result-surface">
      <div className="metadata-row">
        <span className="status-pill">{response.status || "UNKNOWN"}</span>
        {Object.entries(metadata).map(([key, value]) => (
          <span className="metadata-pill" key={key}>
            <b>{key.replaceAll("_", " ")}</b> {Array.isArray(value) ? value.join(", ") : scalar(value)}
          </span>
        ))}
      </div>

      {limited && (
        <div className="state-banner limited">
          <strong>LIMITED / insufficient history</strong>
          <span>The runtime does not yet have enough real observations for a complete result. No value is inferred in the frontend.</span>
        </div>
      )}

      <ValueView value={response.result} />

      {!!response.sources.length && (
        <div className="source-strip">
          <b>Sources</b>
          {response.sources.map((source) => <span key={source}>{source}</span>)}
        </div>
      )}
    </div>
  );
}
