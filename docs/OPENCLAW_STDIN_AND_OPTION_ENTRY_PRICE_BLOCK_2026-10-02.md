# OpenClaw prompt transport and option entry price — 2026-10-02

## Reported defects

The user reported `OSError: [Errno 7] Argument list too long` while running the
shared `investment_synthesis` step from Opportunities (ITUB4) and Strategy Lab
(ITUB4 vs WEGE3). The same OpenClaw client passed the complete prompt as the
`--message` command-line argument.

The Options workspace also did not show the requested option acquisition/sale
price beside the current price in its open positions table.

## Implementation

- OpenClaw now receives the full UTF-8 prompt through stdin with
  `--message-file -`. The prompt is not truncated or placed in process argv;
  deterministic facts, evidence and uncertainty remain intact. OpenClaw's CLI
  documents `-` as stdin for `--message-file` and enforces its own 4 MiB input
  bound.
- Options shows `Preço de aquisição/venda` directly beside `Preço atual`.
  `Position.average_cost` is preferred when populated. Otherwise, unit price is
  computed from execution prices only when all notes for that exact option
  contract have one side and their signed quantity exactly reconciles with the
  current position. The total opening cash flow remains a separate note-backed
  column. Missing or mixed history stays unavailable; no contract multiplier or
  execution price is inferred.

The BTG option-position table contains market premium/value but no average
opening price. The brokerage note is an explicit source for both the unit
execution price and the operation amount. For example, `PCARJ40`, 52,000 bought
at R$ 0.02, total R$ 1,040, must display R$ 0.02 beside current price and R$
1,040 as the note-backed opening total when that quantity reconciles with the
open position. The existing parser preserves side, quantity, unit price and
total amount from this row. A missing/mismatched current position does not
invalidate the note; it only prevents attributing the note to that open lot.

## Verification

- TypeScript/Vite production build: PASS.
- Added regression fixture for the 52,000 × R$ 0.02 brokerage-note row.
- A focused local transport probe sent a 256 KB synthesis input through stdin
  and confirmed argv remains below 1 KB.
- Local `pytest` is unavailable in this sandbox. GitHub CI [#1289 SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37051911828) completed both the full Python test job and React build.
- Ubuntu acceptance: pending for the published block.

## Ubuntu acceptance

After installing this commit, verify:

1. Options → `Posições em aberto`: acquisition/sale price appears beside current
   price when canonical cost or exactly reconciled notes provide it; otherwise
   the value remains explicitly unavailable.
2. Opportunities for ITUB4 and Strategy Lab comparison ITUB4 × WEGE3 complete
   synthesis without `Argument list too long`.

This is an additive transport/UI fix. It does not change V4.3, deterministic
investment calculations, personal-history eligibility, ranking authority or
learning storage.

## Production correction after Ubuntu use

The installed CLI returned `Message file not found: -` from Opportunities,
Market Intelligence and Copilot/B3 Agent. Therefore the stdin convention above
is not supported by this deployed CLI despite the earlier assumption. CI #1289
passed a test that asserted that same convention and did not execute the real
CLI; it was not sufficient compatibility evidence. Superseding fix: pass the
path of a private temporary file containing the complete prompt, and delete it
after every process outcome. See
`UC070809_PRODUCTION_GAP_ANALYSIS_2026-10-02.md` for the root cause and full
UC-07/08/09 production matrix.
