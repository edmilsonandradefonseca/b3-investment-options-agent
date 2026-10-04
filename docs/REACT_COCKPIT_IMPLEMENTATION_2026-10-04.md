# React cockpit implementation

Authority: current attached instructions read in full; three supplied mockups inspected. Later instructions restore Overview, History & Learning and Risk & Stress and allow Copilot to close. The prior five-page restriction is superseded. Backend remains authoritative.

Reuse typed API, AnalysisOutput and domain evidence/history renderers. Refactor shell, routing, result state, tables and charts. Replace option reconciliation and economic arithmetic in React. No backend redesign.

| UC | Surface | Existing endpoints / data | Actions and states | Acceptance |
|---|---|---|---|---|
|01|Portfolio, exposure bars, capital, position detail|portfolio/current including intelligence; capital-profile; orchestrate portfolio snapshot position_pnl|sort/search/select/handoff; UNKNOWN basis and total if absent|exact canonical values|
|02|Options, positions/chain/ledger|options/ledger; options/current; orchestrate Options UC02|filters, quotes, sources; monthly realized data LIMITED|no browser reconciliation, Greeks or P&L|
|03|Opportunities and detail|orchestrate opportunity_assets/objective, opportunity_screen|scan, sort, membership, detail, comparison|exact returned rank and score; no synthetic score|
|04|Strategy Lab|orchestrate comparison_assets, strategies, amount, scenarios|explicit alternatives, assumptions and side-by-side canonical outputs|main workspace results, no client economics|
|05|Market / Regime|orchestrate UC05, market snapshot|explicit analysis, metadata|no fabricated live macro values|
|06|Market / Factors|orchestrate UC06|fetch, sample and LIMITED|association not causation|
|07|History / Operations|history/context ticker/since|ticker/date filter, observed sequence detail|no inferred rolls/expiry or realized outcome|
|08|History / Learnings|history/context + orchestrate UC08|request and admission state|ownership/outcomes missing means LIMITED|
|09|History / Similarity|history/context + orchestrate UC09|request and precedents|no invented candidates/scores|
|10|Market / Research|intelligence/research-context; research/news|stored-first, source links and date search|publication/as_of preserved|
|11|Risk & Stress|orchestrate dashboard_page Risk & Stress UC11 and ticker_price_shocks|explicit shock then canonical results|premises visible, no beta/option repricing inferred|
|12|Contextual Copilot|orchestrate|entity, filters and alternatives; persistent chat; show/close|structured evidence, no order controls|

Order: A shared shell/core; B market context; C observed history; D risk/overview/copilot; E production build, interaction and screenshots at 1920/1440/1366 against active Ubuntu HTTP. Screens remain unaccepted until real browser verification.

Known gaps: ledger has executions/cash flows, no certified monthly/cumulative realized-result series. Snapshot has no portfolio historical-value/benchmark series. No watchlist write endpoint found. These gaps are visible states, not fictitious charts or inert save buttons. Missing learning ownership and calibrated similarity remain LIMITED.
