# BTG received stock distributions — 2026-10-02

## Authority and decision

Verified HEAD 9747346; PR #66 open/draft; GitHub CI #1274 SUCCESS.
The user supplied the current BTG workbook, identified Movimentação > Ações
as the source of received stock dividends/JCP and authorized implementation.
Existing restart/handoff, frozen V4.3 and frontend authorities still apply.

| Capability before code | Classification | Additive action |
|---|---|---|
| Position snapshot import / replacement / API | fully implemented | Reuse portfolio.xlsx and PortfolioContext |
| Received personal dividend/JCP source | missing real data gate resolved by supplied workbook | Exact stock-movement source available |
| Received distributions extraction | missing implementation | Typed statement-period cash observations |
| Portfolio received-income cell | frontend-only gap | Display backend per-ticker net totals and period |
| Announced dividends / entitlement / total return | outside this block; missing wiring/evidence | Preserve existing unavailable state |
| UC-07/08/09 canonical lifecycle/PIT learning | open prior gates | No outcomes or cohorts created by these payments |

## Implementation and semantics

- The existing BTG loader reads the exact Movimentação > Ações section and
  validates the known source headers. It stops at the next section, including
  stock-rental sections, before interpreting their rows.
- Only RECEBIMENTO DIVIDENDOS and JUROS S/CAPITAL become typed personal cash
  observations. RENDIMENTO, restitution of capital, deposits, sales, purchases,
  name changes and other corporate movements are not relabeled as dividends/JCP.
- Each observation preserves ticker, source payment date, source quantity,
  gross amount, net amount and worksheet row reference. No tax rate is invented
  from the gross/net difference. No current holding quantity is used to calculate
  historic per-share income. Missing net amounts stay null and make the affected
  subtotal/total unavailable; an explicit zero remains zero.
- Statement start/end dates come from Capa. Recognized payment dates outside the
  statement period are rejected before replacing the active snapshot. This is
  current statement projection, not proof of historical ingestion availability.
- Backend aggregates net amounts with Decimal by exact ticker. Summaries include
  separate dividend/JCP totals, total net and payment counts. Observed receipts
  for sold tickers remain available in the source context; current-position UI
  joins only exact current tickers. No ticker-change merge is inferred.
- PortfolioContext and GET /portfolio/current carry received_income additively.
  Legacy snapshots lacking the section keep received_income null. Existing
  clients and position/capital engines remain compatible.
- The existing Portfolio column displays received net totals with the statement
  period. Its tooltip shows separate dividend/JCP values and payment count.
  Missing section/backend field displays Indisponível; no matching payment
  displays Sem registro no período, not a claim of zero all-time income.
- The active portfolio.xlsx remains a replacement snapshot. Reimporting an
  overlapping/same statement never appends its payments to another table.
  Within a statement, identical observations are collapsed by exact ticker,
  source payment type/date, quantity, gross and net amounts. Filename/worksheet
  row are not part of this identity, so a repeated row with a new source location
  cannot inflate totals. duplicate_rows_omitted makes exclusions explicit.
  Different tickers or dividend/JCP types remain distinct even with equal amounts.
  The user explicitly requested duplicate protection for overlapping workbooks.
  No schema migration, duplicate ledger, provider/LLM call or background job.

## Verification and deployment boundary

727 Python tests PASS locally; TypeScript/Vite build PASS; git diff --check PASS.
Focused regressions cover source gross/net preservation, ignored movement types,
section boundaries, missing versus explicit-zero values, future payment rejection
duplicate rows, distinct equal-valued ticker/type events, and repeated uploads
with different filenames through the real portfolio import/current endpoints.

The supplied real workbook was imported twice in an isolated API/data directory.
Both responses reproduce the independently inspected period, 32 recognized
payments and the same per-ticker/net totals. This is real-file/local API acceptance,
not a claim of deployment on Ubuntu or desktop visual validation.
No private workbook, account identifier or financial row data is committed.
GitHub CI must independently confirm the published HEAD.

After CI green: update/restart Ubuntu and update the Windows frontend branch.
Load the supplied workbook through Carregar carteira BTG. Existing portfolio.xlsx
is reinterpreted automatically if it already contains the same movement section;
a source reupload is only needed to install this workbook as the active snapshot.
Refresh Portfolio and inspect totals/period/tooltips. No repeated prior OPLAB,
directory-discovery or observed-lifecycle validator is necessary for this UI gate.

Remaining: Ubuntu/desktop acceptance; broader source classifications only with
explicit evidence; announced provents and total-return economics remain separate.
