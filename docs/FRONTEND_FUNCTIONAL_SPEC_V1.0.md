> Revisão normativa de 05/10/2026: [Especificação V1.2](FRONTEND_DECISION_WORKSPACES_SPEC_V1.2.md). Preserva os IDs existentes e explicita as alterações aprovadas de escopo e fluxo. [Gaps e entregas](FRONTEND_V44_GAPS_AND_DELIVERY_2026-10-05.md).

# B3 Investment & Options Agent
# Frontend Functional & UX Specification V1.1 FINAL

**Date:** 2026-09-29  
**Status:** FINAL — approved functional/UX baseline for implementation  
**Target:** React + TypeScript + Vite + Tauri (Windows 11 desktop)  
**Architecture:** B3 V4.0 frozen + V4.1 additive intelligence/runtime layer  
**Reference dashboard:** `feature/v4-dashboard-e2e`  
**Primary UX principle:** decision support, not autonomous execution

---

## 1. Purpose

This document defines the functional, interaction and UX specification for the production frontend of the B3 Investment & Options Agent.

It consolidates the product decisions made during the screen-by-screen UX review and converts them into an implementation-oriented frontend specification.

The frontend must expose the intelligence already available in the B3 backend without duplicating financial calculations in the client.

The final primary navigation is intentionally simplified to five workspaces:

1. **Portfolio**
2. **Options**
3. **Opportunities**
4. **Strategy Lab**
5. **Market Intelligence**

The **Copilot is transversal**. It is not a sixth independent workspace. It remains permanently visible on the right side and receives the context of the active screen, filters and selected asset/position/opportunity.

Capabilities from History & Learning and Risk & Stress remain backend intelligence available to the above workspaces and Copilot, but they are not independent navigation items in V1.

---

## 2. Source baselines

The frontend specification is aligned with:

- `docs/USE_CASES_INVESTMENT_OPTIONS_V2.0.md`
- `docs/USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md`
- `docs/ARCHITECTURE_V4.1.md`
- `docs/DASHBOARD_V4_E2E_STATUS.md`
- `docs/NEXT_STEPS_2026-09-28.md`
- existing React baseline under `frontend/`
- existing visual reference in branch `feature/v4-dashboard-e2e`

The existing V4 E2E dashboard is a **visual and interaction reference**, not the final information architecture.

---

## 3. Product principles

### 3.1 Backend authority

The frontend must not become an investment calculation engine.

Canonical financial facts must come from the backend, including:

- position quantities;
- average acquisition prices;
- market values;
- P&L;
- realized option results;
- option lifecycle state;
- portfolio exposure;
- opportunity scores;
- scenario values;
- risk metrics;
- historical similarity;
- evidence/provenance.

Client-side calculations are allowed only for presentation formatting and harmless UI behavior.

### 3.2 No invented data

If canonical data is missing, the UI must show a clear state such as:

- Not available
- Unknown
- Limited
- Awaiting market data
- Awaiting provider

The UI must never manufacture replacement values.

### 3.3 Human decision authority

The system supports analysis and decision-making.

It does not execute brokerage orders.

No primary action should be named Buy, Sell or Execute.

Appropriate actions include:

- Analyze
- Compare in Strategy Lab
- Add to Watchlist
- Review
- Refresh

### 3.4 Progressive disclosure

The user should first see the information necessary to understand the situation.

Technical provenance, detailed evidence and diagnostics remain accessible, but should not dominate the primary workspace.

### 3.5 Preserve context

Navigating between workspaces must not unnecessarily reset:

- filters;
- sort order;
- selected ticker;
- selected option;
- current page;
- scroll position when practical;
- Copilot conversation context.

Returning from Opportunities to Portfolio should restore the previous Portfolio view without forcing an automatic refresh.

---

# 4. Global information architecture

## 4.1 Application shell

The desktop layout consists of three persistent regions:

| Region | Purpose |
|---|---|
| Left navigation | Main workspaces + data input |
| Main workspace | Tables, charts, analytics and drill-down |
| Right Copilot panel | Permanent contextual conversation and analysis |

Recommended desktop target:

- optimized for 1440×900 and larger;
- minimum supported window approximately 1180×720;
- no mobile-first requirement for V1.

## 4.2 Main navigation

The left navigation contains the primary workspaces plus the operational controls required to connect and load data.

Primary workspaces:

- Portfolio
- Options
- Opportunities
- Strategy Lab
- Market Intelligence

Remove independent entries for:

- Overview
- History & Learning
- Historical Similarity
- Risk & Stress
- Copilot

Portfolio becomes the default landing workspace and absorbs the useful parts of the previous Overview screen.

### 4.3 Persistent operational controls

The left sidebar must also expose, without requiring navigation to another workspace:

- **Load / Update BTG Portfolio**;
- **Load Brokerage Notes** (PDF/ZIP);
- **Available Capital** editor/action;
- **Backend Settings**.

Backend Settings must allow the user to configure the backend connection used by the desktop client, preserving the capability that existed in the original frontend:

- server IP/hostname;
- port;
- resulting base URL preview where useful;
- Save;
- Test connection.

The current active backend and connection status must be visible without exposing credentials. Backend address configuration is a client/runtime setting, not investment state.

---

# 5. Global visual and UX rules

## 5.1 Typography

The current prototype uses text that is too small.

Target minimums:

- normal body/table text: **14–16 px**
- secondary text: **13–14 px**
- navigation labels: **14 px minimum**
- section titles: **18–22 px**
- workspace title: **26–30 px**
- very small 9–11 px text should not be used for core financial information.

## 5.2 Contrast

All buttons, especially upload buttons in the left sidebar, must meet readable contrast standards.

Target: WCAG AA contrast for normal text.

Do not use low-contrast blue-on-blue combinations for operational controls.

## 5.3 Status indication

Remove the generic top cards currently labeled:

- Authority
- Freshness
- Data gaps
- Execution

These are not useful as persistent primary investment information.

Keep only a compact backend connectivity indicator near the workspace header:

- green LED + Connected
- amber/red LED + Offline/Degraded

The connectivity indicator should be driven by backend health.

## 5.4 Refresh

Every analytical workspace has a clear **Refresh** action.

Refresh means:

> Request the latest market/context-dependent information from the backend.

Refresh must **not**:

- replace the BTG portfolio Excel snapshot;
- reimport brokerage notes;
- silently change manually configured capital.

Data source timestamps should appear close to the data they qualify, not as generic dashboard cards.

---

# 6. Global data input area

The left sidebar contains a compact **Data** section.

The mental model is:

> What I own → What I traded → How much capital I can use.

## 6.1 BTG Portfolio Excel

Purpose: load the authoritative current portfolio snapshot.

Rules:

- supports the validated BTG Excel format;
- a successful new import **replaces** the previous current portfolio snapshot;
- the UI must display last successful update date/time;
- the button label should evolve from "Load" to a clearer state such as **Update portfolio** after a snapshot exists;
- failed validation must not replace the last valid snapshot.

Example status:

> Portfolio updated 29/09/2026 09:35

## 6.2 Brokerage notes

Purpose: build/extend historical transactions.

Rules:

- brokerage notes are **additive**, not snapshot-replacing;
- accept PDF files;
- accept multiple files in one selection;
- V1 target: **up to 100 brokerage-note PDFs per batch**;
- also accept one ZIP containing up to 100 brokerage-note PDFs;
- ZIP is optional convenience, not mandatory;
- processing should support partial success;
- valid notes are persisted even if other files fail;
- duplicated notes must not create duplicated economic operations;
- failed filenames must be individually identifiable;
- retry only failed files when possible.

Example batch result:

> 100 sent · 97 processed · 2 duplicates · 1 error

The user must be able to open the error detail and identify the problematic note.

### Recommended technical behavior

For large batches, prefer asynchronous backend ingestion:

1. upload batch;
2. backend returns batch/job ID;
3. frontend polls or subscribes to progress;
4. per-file result is displayed;
5. completed valid files remain committed even when other files fail.

## 6.3 Brokerage capital profile

Add a manual capital input associated with the brokerage account.

Initial fields:

- **Available capital**
- **Minimum reserve**
- **Usable capital = available capital - minimum reserve**

The values are entered manually by the user.

### Persistence decision

Canonical value should be stored in the backend because it is business state used by Portfolio, Opportunities, Strategy Lab and Copilot.

The frontend may cache the latest value locally for UI continuity, but the backend copy is authoritative.

Suggested logical contract:

- broker/account identifier;
- available_capital;
- minimum_reserve;
- updated_at;
- source = manual.

---

# 7. Persistent Copilot

## 7.1 Position

The Copilot remains permanently open on the right side of every workspace.

It is structural, not a pop-up.

The width may be resizable within sensible minimum/maximum bounds, but it must not disappear in the normal desktop experience.

## 7.2 Remove prototype shortcuts

Remove:

- Use workspace query
- What changed?
- Data limitations

## 7.3 Main Copilot action

Add a contextual **Overview** action.

Overview means:

> Analyze the current workspace and selected context using canonical portfolio facts, options positions, market context, relevant opportunities, evidence, historical experience and available learnings.

The exact available inputs depend on the active workspace.

## 7.4 Automatic context

Copilot receives automatically:

- active workspace;
- active filters;
- selected ticker;
- selected stock position;
- selected option;
- selected opportunity;
- Strategy Lab alternatives;
- relevant date range.

The user should not have to repeat visible context in the chat.

Example:

User selects an ABEV option and asks:

> Is it worth closing this position now?

The Copilot should already know which option is selected.

## 7.5 Response structure

Prefer structured answers rather than long undifferentiated prose.

Recommended sections when relevant:

- Summary
- Deterministic facts
- What supports the analysis
- What contradicts it
- Risks
- Relevant precedents/learnings
- Missing/limited information
- Evidence

## 7.6 Model transparency

The main UI should not emphasize internal model names.

User-facing concepts can be:

- Deterministic analysis
- AI synthesis
- Deeper analysis

Exact model/provenance details may be available in an expandable technical detail.

## 7.7 Conversation continuity

Copilot conversation should remain available as the user navigates between workspaces.

When context changes materially, the panel should visibly indicate the new active context, for example:

> Context: ABEV3 / Options

---

# 8. Workspace 1 — Portfolio

## 8.1 Objective

Portfolio is the landing page.

It answers:

> What do I own today, what is it worth, what is my complete economic result, what option obligations exist and how much capital can I use?

Portfolio replaces the separate Overview workspace.

## 8.2 Header

Header contains:

- Portfolio
- backend LED
- Refresh
- portfolio snapshot timestamp
- market data timestamp where applicable.

Do not display generic Authority/Freshness/Data gaps/Execution cards.

## 8.3 Summary area

Useful primary metrics may include:

- current equity portfolio value;
- usable capital;
- minimum reserve;
- capital currently committed to assignments;
- total economic result when canonically available.

Avoid overloading the top area with infrastructure information.

## 8.4 Stocks table

Default sort: **current market value descending**.

Required columns:

| Field | Meaning |
|---|---|
| Asset | B3 ticker |
| Quantity | Current quantity |
| Average acquisition price | Canonical average cost |
| Last price | Most recent canonical market price |
| Price timestamp | As-of date/time |
| Total acquisition value | Canonical acquisition basis |
| Current value | Current market value |
| Stock result | Price appreciation/depreciation result |
| Dividends/JCP received | Cash distributions already received |
| Total economic result | Stock result + received dividends/JCP |
| Total return | Total economic return when available |
| Announced future distributions | Future officially announced dividends/JCP |

Future announced distributions must remain separate from received distributions and must not be included as already-realized return.

Short positions must be visually identified as SHORT and must not be presented as ordinary long holdings.

## 8.5 Stocks chart

Immediately below the stocks table, show:

**Acquisition value vs current value by asset**

Recommended visualization:

- grouped horizontal bars;
- default ordering by current market value descending;
- Top 10 / All control if necessary;
- exact values in tooltip;
- compact labels in the chart.

Selecting a bar selects the corresponding stock row and updates the Copilot context.

## 8.6 Current options table

Portfolio also shows current open options because they are part of current economic exposure.

Required/target columns:

- underlying;
- option ticker;
- PUT/CALL;
- long/short;
- quantity;
- strike;
- expiration;
- DTE;
- average premium paid/received;
- current option price;
- opening cash value;
- current closing value/cost;
- P&L if closed now;
- ITM / ATM / OTM;
- percentage of premium captured for short options when meaningful.

For a sold option, label the current economic value in user language such as:

> R$ X to close

rather than an ambiguous generic "current value".

## 8.7 Option interaction

Selecting an option updates Copilot context.

Typical Copilot questions:

- Is it worth closing this option now?
- How much premium have I already captured?
- What risk remains until expiration?
- What happens if I hold to expiration?

---

# 9. Workspace 2 — Options

## 9.1 Objective

Options is not a duplicate of open positions.

It answers:

> Am I making or losing money with options, in which assets, months and strategies, and what open positions deserve attention?

Primary focus: **performance and history of option strategies**.

## 9.2 Filters and analysis selector

Options must prioritize analytical space over summary KPI cards.

Use a compact horizontal selector/filter bar with:

- period/year/month;
- **asset/underlying** — one asset, multiple selected assets, or All;
- **option/contract** — one specific option, a selected group of contracts, or All;
- PUT/CALL;
- strategy;
- status.

The central monthly-result chart must immediately respond to these selections.

Examples:

- all option operations;
- all PUT sales;
- all options on PETR4;
- a selected group of PETR4 contracts;
- one specific PETR4 option contract.

The selected scope must be visually explicit above or inside the chart so the user always knows what result is being plotted.

Strategy examples:

- Covered call sale
- Uncovered call sale
- Put sale
- Call purchase
- Put purchase
- Other supported structures

Filters update all charts and tables on the page.

Chart clicks may also act as filters.

## 9.3 Screen hierarchy

Do **not** reserve a large top row for the prototype KPI cards such as:

- total result;
- result of the month;
- cumulative result;
- open options;
- upcoming expirations.

The user prefers to dedicate this space to the actual option positions and analytical charts.

The preferred hierarchy is:

1. compact selectors/filters;
2. large monthly-result chart for the selected scope;
3. visible open-options table with as many rows as practical;
4. secondary cumulative/by-asset/by-strategy analysis below or through compact tabs;
5. detailed operation history.

Realized and unrealized results must remain clearly separated wherever displayed.

## 9.4 Monthly result chart

Bar chart around zero.

Purpose:

> Identify positive and negative option-result months.

The chart must react to selected ticker/strategy/filter.

Clicking a month filters the detailed operations below.

## 9.5 Cumulative result chart

Line chart showing cumulative realized option result over time.

This is a true cumulative series:

month 1 → month 1+2 → month 1+2+3 → ...

It must not mix changing mark-to-market of still-open positions into the realized historical series.

## 9.6 Result by asset

Ranking/table or horizontal bars.

Recommended fields:

- asset;
- net realized option result;
- premiums received;
- number of operations;
- positive-operation percentage when statistically meaningful.

Default ordering: result descending.

## 9.7 Result by strategy

Compact table:

| Strategy | Net result | Capital used/committed | Number of operations |
|---|---:|---:|---:|

Purpose:

> Understand whether the user's historical option performance differs by strategy.

## 9.8 Upcoming expirations / open risk

Show open positions grouped by expiration period.

Example:

> October · 4 positions · R$ X assignment exposure

Useful per-position indicators:

- percentage of premium captured;
- DTE;
- moneyness;
- assignment exposure;
- current cost to close.

## 9.9 Detailed operations table

The lower section contains the operations matching the active filters.

Target fields:

- underlying;
- option ticker;
- strategy;
- PUT/CALL;
- long/short;
- quantity;
- strike;
- opening date;
- closing/expiration/exercise date;
- premium;
- closing value;
- gross result;
- fees when known;
- net result when known;
- final status.

### Default accounting convention for V1

Unless the backend canonical model defines otherwise:

- realized result is attributed to the period in which it becomes realized through close, expiration or exercise;
- gross and net results should be distinct when costs are available;
- covered/uncovered classification should be point-in-time, using the state at the relevant operation date.

## 9.10 Integrated result by asset

The primary Options analytics must remain pure options performance.

However, an optional integrated view may show:

> stock price result + dividends/JCP received + options result = consolidated economic result for the asset.

This integrated view must never replace the isolated options result.

---

# 10. Workspace 3 — Opportunities

## 10.1 Objective

Opportunities answers:

> Given current market conditions, my portfolio and the system's canonical analysis, which assets or strategies deserve further analysis now — including assets I do not currently own?

The workspace is a **discovery and prioritization funnel**, not an order recommendation screen.

## 10.2 Analyze any asset on demand

At the top of the page, provide a prominent field:

**Analyze asset**

The user may enter:

- B3 ticker;
- company name;
- asset not present in the current opportunity ranking.

Action:

**Analyze**

The result should open in the same opportunity-analysis experience.

If the asset was not originally selected by the discovery pipeline, label it as an **on-demand analysis**.

The UI should not fabricate eligibility. If the asset fails canonical filters, show why.

## 10.3 Filters

Avoid the technical label "Universe".

Use plain-language filters.

Recommended visible filters:

- Strategy type
- Risk level
- Liquidity

Optional/advanced filter:

- Search scope: All analyzed B3 assets / Portfolio / Watchlist

The default should not artificially restrict discovery to the current portfolio.

## 10.4 Summary area

Keep:

- **Assets analyzed**

Remove from the primary summary:

- opportunities by sector;
- eligible opportunities count;
- outside-portfolio count;
- capital required.

The user decides how much to invest. Capital is therefore not a primary opportunity-ranking KPI.

## 10.5 Visual opportunity map

Use a visual **risk vs opportunity-score** map.

Recommended scatter plot:

- X axis: risk score;
- Y axis: deterministic opportunity score;
- point: asset/strategy;
- optional point encoding may represent liquidity if useful and readable.

Purpose:

> See the trade-off between opportunity strength and risk without relying only on a table.

Do not imply that the visually upper-left point is automatically a trade recommendation.

## 10.6 Opportunity distribution

A compact risk/opportunity distribution visualization may remain because the user explicitly found it useful.

Avoid decorative sector charts with low decision value.

## 10.7 Opportunity ranking

The ranking must contain an explicit **Rank / Classification** column (1, 2, 3, ...), generated by the canonical opportunity-ranking pipeline.

The user must be able to see immediately where each opportunity stands in the current filtered analysis.

Target columns:

- asset;
- strategy;
- deterministic opportunity score;
- risk score;
- liquidity;
- portfolio impact indicator;
- why it appeared;
- evidence quality/status.

Do not include "capital required" as a primary ranking column.

Suggested row actions:

- Open analysis
- Compare in Strategy Lab
- Add to Watchlist

No Buy/Sell/Execute action.

Selecting a row also updates the Copilot context automatically.

## 10.8 Opportunity deep-dive

Clicking **Open analysis** opens a detailed opportunity view while keeping:

- left navigation;
- backend LED / Refresh;
- permanent right Copilot.

### Header

Show:

- asset/company;
- current canonical price;
- strategy being analyzed;
- opportunity score;
- risk score;
- back to ranking;
- Compare in Strategy Lab;
- Add to Watchlist.

### Block A — Why it appeared

Short, evidence-backed drivers.

Examples:

- valuation;
- momentum;
- market regime;
- liquidity;
- volatility;
- relevant event;
- portfolio diversification contribution.

### Block B — Score decomposition

Visual bars for components used by the deterministic ranking.

Only show components actually provided by the backend.

Purpose: avoid a black-box score.

### Block C — Portfolio impact

Because the user defines investment amount, do not assume a fixed capital allocation.

Provide an optional **Amount to simulate** input.

Once an amount is provided, request backend evaluation for:

- concentration impact;
- capital utilization;
- diversification impact;
- relevant portfolio overlap/exposure.

### Block D — Supporting vs contradicting evidence

Two visually distinct columns:

- Supports
- Contradicts / Risks

This makes disagreement and uncertainty visible.

### Block E — Related strategies

Show relevant alternatives for the same asset when supported, for example:

- buy stock;
- sell put;
- maintain cash/do nothing.

Each alternative may be sent to Strategy Lab.

### Block F — Evidence and events

Table/timeline:

- source/event;
- date;
- affected asset;
- support/contradict/update/no-impact;
- source reference.

### Copilot behavior in deep-dive

Copilot automatically switches to the selected asset/opportunity.

Typical questions:

- Why did this opportunity appear?
- What is the main risk?
- What contradicts the thesis?
- Compare stock purchase vs put sale.
- How would this affect my current portfolio?

---

# 11. Workspace 4 — Strategy Lab

## 11.1 Objective

Strategy Lab answers:

> Before I decide, how do alternative actions compare using the same canonical assumptions and portfolio context?

It is the comparison workspace.

## 11.2 Entry paths

Strategy Lab may be opened from:

- Opportunities;
- Portfolio stock selection;
- Portfolio option selection;
- Options;
- direct user configuration.

## 11.3 Alternatives

Strategy Lab must support comparisons **across different assets as well as different strategies**.

V1 should support at least two comparable alternatives.

Examples:

- buy ITUB4 vs buy WEGE3;
- sell a PUT on PETR4 vs sell a PUT on ITUB4;
- buy stock A vs sell PUT on stock B;
- buy stock vs sell PUT on the same underlying;
- hold an option vs close it;
- strategy A vs strategy B;
- act vs do nothing.

Each alternative therefore has its own:

- asset/underlying;
- strategy;
- quantity or capital assumption;
- contract/strike/expiration when applicable.

The user supplies amount/quantity assumptions where needed.

## 11.4 Comparison surface

For each alternative, display only metrics supported by the backend:

- capital required/allocated;
- return / expected return when available and properly qualified;
- risk;
- volatility;
- maximum loss when available;
- payoff by explicit scenario;
- liquidity;
- portfolio impact;
- historical similarity;
- experience confidence;
- assumptions;
- evidence.

The comparison must normalize metrics where necessary so that alternatives using different assets or strategy types can be compared without misleading scale effects.

The frontend does not compute these metrics.

## 11.5 Scenario comparison

Show a scenario table/chart when the backend supplies explicit scenarios.

Example structure:

| Scenario | Alternative A | Alternative B | Difference |
|---|---:|---:|---:|

Scenarios are analytical assumptions, not probabilities unless a validated backend source explicitly provides probabilities.

## 11.6 Comparative ranking

The user wants Strategy Lab to produce an explainable classification such as **1st / 2nd** between the alternatives being analyzed.

This is feasible, but it requires a deterministic ranking contract in the backend. The current StrategyComparison foundation compares deltas and intentionally does not apply a ranking.

The frontend must therefore **not invent a winner** and the Copilot/LLM must not create an unsupported rank.

The target backend ranking should combine explicit comparable dimensions such as:

- return;
- risk;
- volatility;
- maximum loss/downside;
- liquidity;
- capital efficiency;
- portfolio impact;
- scenario robustness.

The ranking methodology and weights must be visible and versioned. Where user preference matters, the Strategy Lab may allow an explicit objective/profile (for example balanced, lower risk, higher return), but must never silently change weights.

The UI should show:

- **1st / 2nd / ...** classification;
- overall deterministic comparison score;
- component scores;
- why one alternative ranked above another;
- important trade-offs and contradictory evidence.

If the backend cannot produce a validated ranking for the compared alternatives, show **Comparison available — ranking unavailable** rather than guessing.

## 11.7 Decision support

Use:

- side-by-side cards;
- rank badges when canonically available;
- return × risk visualization;
- volatility;
- delta indicators;
- payoff/scenario chart;
- assumptions;
- supporting and contradicting evidence.

The Copilot may explain the ranking and trade-offs using the active comparison context, but it does not determine the canonical rank.

---

# 12. Workspace 5 — Market Intelligence

## 12.1 Objective

Market Intelligence answers:

> What market environment am I operating in, what changed, and which external factors/events are relevant to my portfolio and opportunities?

This workspace provides context rather than direct trade execution.

## 12.2 Primary market context

Recommended top area:

- market regime;
- Ibovespa / broad equity context;
- Selic/CDI;
- USD/BRL;
- volatility;
- foreign investor flow;
- oil;
- iron ore;
- other factors supported by canonical providers.

Do not show metrics for which reliable current data is unavailable.

Each market metric should carry its own appropriate as-of information.

## 12.3 Regime panel

Show the current regime in understandable language, with the underlying dimensions supplied by the backend, such as:

- trend;
- volatility;
- risk appetite;
- rates;
- FX;
- commodity context.

Avoid presenting an opaque regime label without drivers.

## 12.4 Market trends

Use line charts for time-series data such as:

- rates;
- FX;
- index;
- foreign flow;
- volatility.

Allow useful time ranges where provider data exists.

## 12.5 Relevant news and events

Prioritize events that affect:

- current portfolio;
- selected watchlist;
- current opportunities;
- major market regime drivers.

Each event should show:

- publication/event date;
- source;
- affected asset/sector;
- relationship to current thesis when known;
- support/contradict/update/no-impact classification when available.

## 12.6 Factors

Factor intelligence may be surfaced here when statistically validated.

Clearly distinguish:

- observed association;
- statistical evidence;
- causal claim.

Association must never be labeled as causation without appropriate evidence.

## 12.7 Copilot behavior

Copilot Overview in this workspace should synthesize:

- current regime;
- important changes;
- relevant market drivers;
- impact on portfolio/opportunities;
- major events;
- uncertainty.

---

## 12.8 Asset Intelligence — dedicated asset analysis

Market Intelligence includes a dedicated **Asset Analysis** view. This is not a new top-level workspace; it is a sub-view of Market Intelligence.

Its purpose is to answer:

> What is happening with this specific stock, technically and fundamentally, what are relevant institutions saying, and what news/events may affect it?

### Asset selector and header

The user can search/select a supported B3 ticker or company. The header shows, when canonically available:

- ticker and company;
- sector/industry;
- current price and daily change;
- last market update;
- market capitalization;
- P/L;
- P/VP;
- EV/EBITDA;
- dividend yield;
- ROE;
- 52-week range;
- Add to Watchlist.

### Price chart and configurable horizon

The main visual is an interactive price/candlestick chart with volume.

Required horizons include at least:

- 1 week;
- 1 month;
- 3 months;
- 6 months;
- 1 year;
- longer history / All when data exists.

The user may overlay supported technical indicators. Exact price/volume values must come from canonical market data.

### Technical analysis

Display technical indicators supported by the backend, such as:

- RSI;
- MACD;
- moving averages (20/50/200);
- stochastic oscillator;
- Bollinger Bands;
- ADX;
- volume;
- other validated indicators.

Show both the raw value and a concise interpretation where a deterministic rule exists. Provide an overall trend summary by useful horizons (short/medium/long term) without fabricating unsupported signals.

### Fundamental analysis

Provide tabs/sections for:

- summary;
- income statement;
- balance sheet;
- cash flow;
- indicators/multiples;
- dividends/JCP.

Relevant metrics may include revenue, EBITDA, net income, margins, leverage, ROE, valuation multiples and dividend yield, only when reliable data is available.

### Institutional research and target prices

Provide a **Research / Target Price Summary** consolidating available, attributable and sufficiently current research from institutions such as:

- BTG Pactual;
- XP Investimentos;
- Itaú BBA;
- Safra;
- other supported/reliable research sources.

For each institution show only verified fields that are actually available:

- institution;
- recommendation/rating;
- target price;
- report/publication date;
- implied upside/downside versus the current canonical price;
- source/reference.

The UI may show descriptive aggregates such as mean/median target price and rating distribution when enough comparable reports exist.

**Critical rule:** the system must never invent, infer or silently carry forward an institution's recommendation or target price. If the current report cannot be verified, show it as unavailable/stale rather than estimating it. Any aggregate must disclose the reports and dates included.

### News and events for the selected asset

Show recent relevant news and upcoming events, including when available:

- earnings/results;
- dividends/JCP;
- shareholder meetings;
- regulatory events;
- sector/company events;
- macro/commodity events with direct relevance.

Each item should carry date/time, source and relevance/relationship to the asset when supported.

### Peer comparison

Allow comparison with relevant peers when canonical comparable data exists. Comparison may include valuation, profitability, leverage, growth and market performance.

### Copilot context

When Asset Analysis is open, Copilot automatically receives the selected ticker and visible analysis context.

Typical questions:

- Summarize PETR4.
- What is the current technical trend?
- What are the main fundamental strengths and risks?
- Compare the target prices published by the available research houses.
- What changed recently in the investment thesis?
- What upcoming events matter?
- Compare PETR4 with relevant peers.

Copilot synthesizes attributable evidence; it must not fabricate broker research or target prices.

### Asset Analysis acceptance criteria

Accepted when:

- a supported ticker can be searched/selected;
- the price chart supports at least 1W, 1M and 1Y horizons;
- technical indicators are displayed from canonical data;
- fundamental metrics are available where supported;
- institutional target prices/recommendations include institution, date and source;
- stale/unavailable research is clearly identified rather than inferred;
- relevant asset news/events are visible;
- Copilot automatically receives the selected asset context.

---

# 13. Cross-workspace interaction model

## 13.1 Selection propagation

Selecting an entity should propagate context across the app.

Examples:

- select ABEV3 in Portfolio → Copilot knows ABEV3;
- open ABEV3 opportunity → Copilot knows opportunity context;
- send ABEV3 to Strategy Lab → Strategy Lab opens preconfigured;
- return to Portfolio → prior Portfolio sort/filter remains.

## 13.2 Watchlist

Opportunities may add an asset to a simple Watchlist.

Watchlist is a discovery/context mechanism, not a portfolio position.

It may influence:

- Opportunities search scope;
- Market Intelligence relevance;
- Copilot context.

## 13.3 No hidden refresh

Navigation should not silently trigger expensive intelligence recomputation.

Refresh is explicit unless background updates are already available from scheduled backend jobs.

---

# 14. Frontend state model

The frontend needs three distinct state classes.

## 14.1 Canonical server state

Examples:

- portfolio snapshot;
- positions;
- prices;
- option results;
- opportunity results;
- market intelligence;
- evidence;
- capital profile.

Use backend as authority.

Recommended implementation approach: query/cache layer such as TanStack Query or equivalent.

## 14.2 UI session state

Examples:

- active workspace;
- active tab/filter;
- selected ticker;
- selected opportunity;
- sort order;
- Copilot panel width;
- table display preferences.

A lightweight client store may be used.

## 14.3 Persistent local preferences

Examples:

- panel width;
- optional column visibility;
- last non-sensitive UI preferences.

Do not treat local persistence as authoritative financial state.

---

# 15. Recommended React component architecture

Conceptual structure:

- AppShell
  - TopBar
    - BackendStatus
    - RefreshAction
  - Sidebar
    - MainNavigation
    - DataInputs
      - PortfolioImport
      - BrokerageNotesImport
      - CapitalProfileEditor
  - WorkspaceRouter
    - PortfolioWorkspace
    - OptionsWorkspace
    - OpportunitiesWorkspace
    - OpportunityDetail
    - StrategyLabWorkspace
    - MarketIntelligenceWorkspace
  - CopilotPanel
    - ContextIndicator
    - OverviewAction
    - Conversation
    - Composer

Shared analytical components:

- FinancialTable
- MetricCard
- TimeSeriesChart
- ComparisonBarChart
- OpportunityScatter
- EvidenceList
- StatusBadge
- EmptyState
- ErrorState
- LoadingState
- LimitedDataBanner
- TimestampLabel

For production-quality financial tables, a table library such as TanStack Table is recommended.

For charts, use a single consistent production charting library with support for:

- bar;
- line;
- scatter;
- tooltip;
- zoom/selection where useful;
- responsive sizing.

---

# 16. API and contract requirements

## 16.1 Typed client

All frontend/backend interaction should go through typed TypeScript contracts.

Avoid ad-hoc untyped JSON rendering as the final production UX.

The existing generic JSON/result renderer may remain only as a development/debug fallback.

## 16.2 Required backend capability groups

The frontend expects contracts for:

- health/connectivity;
- portfolio snapshot/read;
- portfolio import;
- brokerage-note batch import;
- brokerage capital profile;
- market refresh/state;
- current option positions;
- option history/performance;
- opportunity scan;
- on-demand asset opportunity analysis;
- opportunity detail/evidence;
- strategy comparison;
- market intelligence;
- Copilot/orchestration.

Exact endpoint names may follow existing server conventions and should be finalized during implementation.

## 16.3 Financial authority metadata

Material analytical responses should support metadata where applicable:

- as_of;
- quality status;
- source/evidence references;
- assumptions;
- limitations.

These should be displayed contextually, not as permanent generic dashboard cards.

---

# 17. Loading, error and limited-data behavior

Every major surface must support:

- loading;
- refreshing while retaining prior valid data when safe;
- empty;
- offline;
- partial/limited;
- error;
- stale/old data when backend explicitly indicates it.

### Examples

No brokerage notes yet:

> No brokerage-note history loaded.

Provider missing Greeks:

> IV/Greeks unavailable for this contract.

Batch partially failed:

> 97 of 100 processed. Review 3 files.

Backend offline:

> Backend unavailable. Last loaded data remains visible where safe, clearly marked as not refreshed.

---

# 18. Accessibility and readability

Requirements:

- readable font sizes;
- AA-level text contrast;
- do not communicate gains/losses or status by color alone;
- use icons/text in addition to color;
- keyboard-accessible controls where practical;
- visible focus states;
- financial numbers right-aligned in tables;
- consistent BRL and percentage formatting;
- negative signs always explicit;
- avoid excessive decimal precision.

---

# 19. Mapping to the 12 backend use cases

| Frontend surface | Primary backend use cases |
|---|---|
| Portfolio | UC-01, UC-02 |
| Options | UC-02, UC-07, UC-08 |
| Opportunities | UC-03, UC-05, UC-06, UC-09, UC-10, UC-11 |
| Strategy Lab | UC-04, UC-09, UC-11 |
| Market Intelligence | UC-05, UC-06, UC-10 |
| Transversal Copilot | UC-12 + contextual outputs from UC-01…UC-11 |

UC-07/08/09/11 remain backend capabilities even when not exposed as independent top-level screens.

---

# 20. Acceptance criteria by workspace

## 20.1 Portfolio

Accepted when:

- left sidebar exposes BTG Portfolio, Brokerage Notes, Available Capital and Backend Settings;
- Backend Settings allows IP/hostname + port configuration and connection test;
- BTG snapshot last-update time is visible;
- stocks are sorted by current value by default;
- stock table contains acquisition/current/economic-return fields;
- received dividends/JCP are separated from future announced distributions;
- acquisition-vs-current chart is interactive;
- current option positions are visible;
- navigation away/back preserves state;
- selecting stock/option updates Copilot context.

## 20.2 Options

Accepted when:

- asset selector supports one asset, a selected group or All;
- option selector supports one contract, a selected group or All;
- period/asset/option/strategy filters update the monthly-result chart and workspace;
- large prototype KPI row is removed in favor of more chart/open-position space;
- realized and open P&L are separated;
- monthly and cumulative realized result charts work;
- result by asset and strategy is available;
- upcoming expirations/open risk is visible;
- clicking a chart can filter drill-down;
- detailed operation history reconciles with canonical backend data;
- Copilot receives active filters and selected operation.

## 20.3 Opportunities

Accepted when:

- the user can scan ranked opportunities with an explicit rank/classification column;
- assets outside the current portfolio are considered;
- the user can request analysis of any supported asset manually;
- Assets analyzed is visible;
- risk vs score visualization is interactive;
- low-value sector/eligible/outside-portfolio/capital-required summary cards are absent;
- Open analysis provides evidence-backed drill-down;
- Strategy Lab handoff works;
- Copilot receives selected opportunity context.

## 20.4 Strategy Lab

Accepted when:

- at least two alternatives can be compared, including alternatives on different assets;
- return, risk and volatility are visible when canonically available;
- deterministic rank (1st/2nd/...) is shown only when a validated backend ranking contract is available;
- the user controls amount/quantity assumptions;
- canonical comparison values come from backend;
- scenario deltas and assumptions are visible;
- evidence/limitations are available;
- no automatic trade execution exists;
- Copilot can explain the active comparison.

## 20.5 Market Intelligence

Accepted when:

- market regime is understandable and driver-based;
- supported macro/market time series are visualized;
- portfolio/opportunity-relevant news/events are prioritized;
- data timestamps are visible where relevant;
- factor claims distinguish association from causation;
- Market Intelligence includes the approved Asset Analysis sub-view with configurable price horizon, technicals, fundamentals, attributable research/target prices, news/events and contextual Copilot;
- Copilot can synthesize current market context.

---

# 21. Implementation priorities

Recommended sequence:

### Phase 1 — Shell and Portfolio
- simplify navigation;
- improve typography/contrast;
- backend LED;
- persistent Copilot shell;
- BTG import;
- brokerage-note batch import;
- manual capital profile;
- Portfolio tables/charts.

### Phase 2 — Options
- filters;
- realized/open KPIs;
- monthly/cumulative charts;
- by-asset/by-strategy analysis;
- expirations;
- operation drill-down.

### Phase 3 — Opportunities
- opportunity ranking;
- risk-score visualization;
- analyze-any-asset input;
- opportunity detail;
- watchlist;
- Strategy Lab handoff.

### Phase 4 — Strategy Lab
- alternative configuration;
- comparison views;
- scenarios;
- evidence/assumptions.

### Phase 5 — Market Intelligence and Asset Intelligence
- regime;
- market/macro charts;
- news/events;
- factor surfacing;
- dedicated Asset Analysis view;
- technical indicators and fundamental analysis;
- attributable institutional research/target-price summary;
- asset news/events and peer comparison;
- cross-workspace UX polish;
- performance/accessibility validation.

---

# 22. Explicit exclusions for V1 navigation

The following are intentionally **not separate top-level screens**:

- History & Learning
- Historical Similarity
- Risk & Stress
- standalone Copilot page

Their underlying backend intelligence remains usable contextually in Portfolio, Options, Opportunities, Strategy Lab, Market Intelligence and Copilot.

---

# 23. Final navigation model

    B3 Investment Copilot
    |
    +-- Portfolio
    |
    +-- Options
    |
    +-- Opportunities
    |     |
    |     +-- Opportunity Detail
    |
    +-- Strategy Lab
    |
    +-- Market Intelligence
    |
    +-- Persistent Copilot (right panel on every screen)

Data inputs remain globally accessible:

    BTG Portfolio Excel
    Brokerage Notes (PDF / ZIP, up to 100 notes per batch)
    Brokerage Capital Profile

---

# 24. Functional UX flow

    Portfolio / Market / History / Evidence
                    |
                    v
            Canonical backend
                    |
                    v
               Frontend
        +-----------+-----------+
        |           |           |
        v           v           v
     Observe     Discover     Compare
     Portfolio   Opportunities Strategy Lab
        |           |           |
        +-----------+-----------+
                    |
                    v
               Copilot
          contextual synthesis
                    |
                    v
             Human decision

The frontend is therefore designed as a **decision-support workstation**, not a brokerage execution terminal.

---

# 25. Implementation handoff rule

During frontend development:

1. Do not reopen the frozen V4 architecture.
2. Do not move investment calculations into React.
3. Do not infer missing canonical values in the client.
4. Prefer domain-specific financial surfaces over generic JSON.
5. Keep Copilot contextual and transversal.
6. Preserve explicit human decision authority.
7. Treat provider/calibration gaps as visible data limitations, not UI defects.
