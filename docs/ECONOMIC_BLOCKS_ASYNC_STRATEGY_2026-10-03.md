# Four economic blocks and asynchronous strategy — 2026-10-03

Authority: user's four-block scope, FRONTEND_FUNCTIONAL_SPEC_V1.0.md (V1.1 FINAL), DECISION_WORKSPACES_DELIVERY_PLAN_2026-10-02.md and ARCHITECTURE_V4.3.md. Finish backend contracts before rebuilding the frontend; visual acceptance will use the replacement frontend. No new canonical ledger or financial calculation in React.

## Implemented functional boundary

1. Issuer dividends: qualify available per-share events with source, announcement, record/ex and payment dates. Separate observed trailing distributions, officially announced future payments, conditional new-purchase entitlement and missing forecasts. Available ITUB4 events work; BBDC4 BRAPI returns HTTP403. Neither a missing event nor partial coverage means zero dividends.
2. Institutional targets: read qualified structured reports from existing Qdrant. New primary XP report adapter extracts an explicit amount and end-year horizon only from a same-ticker report paragraph, with exact institutional URL, explicit report-version modified timestamp, source content hash and deterministic report ID. Public factual records were acquired in the development workspace; Ubuntu direct XP access returns HTTP403. The reviewed factual transport preserves original acquisition dates and does not redistribute report bodies. This is genuine source evidence, not a fixture. BTG/Safra/Itaú acquisition adapters and broad new-report discovery remain open.
3. Economic decisions: BUY×BUY keeps explicit cost-aware user scenarios and their own conditional maximin ranking. Added source-backed price-only institutional upside/gain, descriptive paid yield, conditional announced gross income, integer sizing, cash conservation and purchase effects on signed stock quantities, recorded cash and gross position share, including related options. Missing entry costs stop sizing. Gross position share is not NAV, sector concentration or option risk netting. Opportunities receives the same dimensions and a separately requested, same-institution/same-horizon target-potential comparison; its prior observed-risk/liquidity rank is unchanged. Institution opinions do not authorize expected return, calibrated probabilities or overall investment superiority.
4. Validation/activation: full Python/React CI, real Ubuntu ingestion, zero-model Opportunities/BUY calculations, then a senior comparison and senior Opportunities synthesis with canonical linked assessments. Candidate tests do not establish active-systemd deployment. Restart authentication and active HTTP acceptance are separate. Replacement frontend and Windows visual E2E remain outstanding.

## Producer/consumer strategy

- Scheduler owns periodic acquisition, not UI requests. Existing nightly script now invokes PrimaryTargetRefreshJob for reviewed URLs belonging to monitored assets. Each source failure is isolated and visible.
- Primary collectors acquire reports and version/source metadata. Current deterministic XP parser admits an explicit structured target; it does not require a model to extract a supported numerical sentence.
- Qualified target facts are projected into the existing b3_evidence_768_hybrid collection. Reviewed fallback preserves publication and first acquisition timestamps and fails qualification when stale; an HTTP403 is never labeled a successful fresh download.
- Versioned factual report events enter the existing LocalEvidenceQueue under /opt/b3-runtime/data/derived/local_evidence_analyst. A repeated version does not produce a new pending model request.
- Existing DeepSeek worker consumes that queue separately, respecting shared-host reasoning locks and deferring when busy. It produces an analytical dossier; it cannot invent or override authoritative numerical fields. Model extraction proposals for unsupported layouts require a verified source-span admission policy before becoming financial facts.
- Screens read qualified target evidence. Financial arithmetic remains Python. Senior synthesis interprets sourced facts, explicit scenarios, contradictions and gaps when requested.

## Explicit limits to continuous operation

Code integration with the nightly producer is not proof the production timers are installed/active or that DeepSeek consumed these new report events. Real queue admission and actual worker consumption must be recorded separately.

Current target refresh covers reviewed report URLs, not discovery of every new institutional report. The Ubuntu source restriction also prevents claiming autonomous fresh XP acquisition. Provide a working permitted institutional/provider acquisition channel or import newly reviewed primary records; never extend stale validity or backdate retrieval to hide this restriction.

Dividends currently retain live collection in the purchase/screen path. Completing an asynchronous dividend producer plus reuse of its qualified projection is a remaining implementation step. This checkpoint must not be read as all four blocks complete or as completion of AC-01–AC-28.

## Frontend sequence

After backend activation and remaining data-producer decisions, rebuild against the saved final functional/UX specification: five workspaces, central economic output, permanent contextual Copilot, explicit source/date/horizon and missing-data states, preserved comparison context and backend-only financial calculations. Verify Windows rendering and the actual interaction flows before closing visual acceptance.

## Verified increment

Code dad435402bec95f163831dac055eb38b497d50e5. CI 37161675294 SUCCESS: 887 Python tests, 8 warnings, 10.64 seconds; React build/render checks PASS. Local full suite also PASS. Real Ubuntu workflow 37161671894 SUCCESS: reviewed primary reports projected to production Qdrant; production LocalEvidenceQueue admission ENQUEUED on first accepted import and ALREADY_QUEUED on repeated versions. Actual DeepSeek consumption was not executed/verified in this gate.

Candidate BUY economic comparison: HTTP200, 2020.5 ms, zero LLM, cash conservation PASS. Candidate sourced Opportunities: HTTP200, 2005.6 ms, two institutional targets, conditional same-institution/horizon target-potential ranking, zero LLM, cash conservation PASS. Actual senior BUY synthesis: HTTP200, two linked assessments, 84275.3 ms. Actual senior Opportunities synthesis: HTTP200, two linked assessments, 67465.2 ms. These prove structured coverage, not independently scored decision quality or superiority to ChatGPT.

Ubuntu checkout updated to dad4354; automatic systemd restart remains blocked by interactive authentication. Operator activation: `sudo systemctl restart b3-runtime.service`. Subsequent focused active HTTP acceptance must verify the new sourced economic fields in both workspaces. The workflow's existing active HTTP health/chart/regression checks passed against the previous process; they do not establish activation of this new code.
