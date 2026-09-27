# Dashboard V4 E2E

Read-only Streamlit interface for the frozen B3 V4 domain.

## Authoritative input contract

The dashboard has two independent upload flows.

### 1. BTG Portfolio — current state

The BTG XLSX is the authoritative source for current positions.

Only the `Renda Variavel` sheet is relevant, and only these two sections are imported:

- `Posição > Ações`
- `Posição > Opções`

All other workbook sections are outside the B3 portfolio contract, including movements, stock lending, guarantees, BDR, ETF, fixed income, funds, current account and flexible options.

The statement end date is metadata for `as_of`.

The loader preserves broker identifiers. Portfolio Intelligence applies an explicit economic identity resolver only when aggregating exposures and risk; source fields are never silently rewritten.

### 2. Brokerage Notes — historical state

Brokerage-note PDFs are historical transaction evidence.

They are parsed into option transactions and appended to an idempotent SQLite ledger. Brokerage notes do not replace or override the BTG current-position snapshot.

The historical ledger preserves:

- trade date
- option ticker
- BUY / SELL side
- traded quantity
- execution price
- signed total amount
- brokerage note number
- broker/source provenance

Repeated import of the same economic transaction is deduplicated by fingerprint.

## Source precedence

For current holdings:

```text
BTG Portfolio > Renda Variavel > Posição > Ações / Opções
```

For historical execution price and lifecycle reconstruction:

```text
Brokerage Notes -> append-only option ledger
```

The two sources answer different questions:

- BTG: what is held now?
- Brokerage Notes: how did the position get here and at what execution prices?

A mismatch is evidence to reconcile, not permission to rewrite source data.

## Current E2E path

```text
BTG XLSX
  -> BtgRendaVariavelLoader
  -> PortfolioContext
  -> Portfolio Intelligence / Options Intelligence

Brokerage Note PDFs / ZIP batch
  -> bounded upload / per-PDF extraction
  -> BrokerageNoteParser
  -> OptionTransactionLedger
  -> historical BUY/SELL prices
  -> future operation reconstruction / realized P&L
```

The UI does not manufacture opportunities when analytical market/valuation/options inputs are absent.

## Runtime validation

The current runtime gate is:

1. open Streamlit
2. upload a real BTG portfolio XLSX
3. confirm only `Posição > Ações` and `Posição > Opções` were loaded
4. upload up to 10 brokerage-note PDFs, or one ZIP for a larger historical batch
5. confirm BUY/SELL rows and execution prices appear in Options Intelligence
6. repeat the same PDF/ZIP batch and confirm the ledger remains idempotent
7. validate reconciliation and historical operation reconstruction

## Run locally

```bash
cd /opt/b3-investment-options-agent
git switch feature/v4-runtime-integration
git pull --ff-only origin feature/v4-runtime-integration
.venv/bin/streamlit run mvp/dashboard/app.py
```

The dashboard is dynamic; `B3_AGENT_PORTFOLIO_FILE` remains only an optional fallback for development and is not the primary user workflow.
