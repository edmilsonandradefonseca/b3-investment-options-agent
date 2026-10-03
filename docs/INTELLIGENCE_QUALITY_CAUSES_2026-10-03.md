# Intelligence quality: diagnosed causes and bounded correction

Authority: V4.3, functional specification, decision workspace delivery plan and
SESSION_CHECKPOINT_B3_INTELLIGENCE_2026-10-02.md. This block is not acceptance of
AC-01–AC-28 or proof of superiority over ChatGPT.

## Confirmed causes from the GitHub source

| Layer | Evidence | Consequence / correction |
| --- | --- | --- |
| Presentation | AnalysisOutput displayed specialist summaries but omitted findings, risks and their references. Synthesis conflicts and proposal opportunity_cost, capital_impact, confidence and invalidation_conditions were only accessible through debug JSON. | Render these supplied fields plus deterministic risk validation in the shared output used by all three screens and Copilot. |
| Unknown preservation | Covered-call incremental capital rendered null as zero. | Missing capital now displays unavailable. |
| Prompts | Generic specialist and synthesis prompts did not require alternative-specific implications, supporting and contradicting evidence, or reasons a comparison cannot conclude. | Strengthen the existing contracts without financial calculations or new schema authority. Request Portuguese analysis and observable invalidation conditions. |
| Opportunities engine | LiveOpportunityService selects at most 20 options in expiry/strike/ID technical order; economic ranking is explicitly deferred. No broad stock ranking or allocation is supplied. | Still open: a versioned deterministic policy, eligible universe and objective/restrictions. Prompt improvement cannot close this gap or turn first candidate into best investment. |
| Market data | Historical chart exists. Verified institutional target loader is absent; fundamentals and research may be partial or unavailable. | Still open: source-backed target ingestion and decision inputs. No model-generated substitute targets. |
| Copilot / layout | Conversation responses are rendered in the right sidebar; comparison form responses are central. Navigation clears analysis and lacks structured handoff of alternatives. | Still open: explicit central comparison continuation and workspace continuity. No inferred multi-leg economics in this block. |
| Senior routing | Three specialists, committee and reasoning are used by default, with optional synchronous João perspective. There is no new comparative quality baseline. | Keep existing routing; run one bounded real senior stock comparison with stage telemetry before runtime update. Do not equate successful HTTP or nonempty text with quality. |

## Verification

CI runs Python regressions, React build and a server-rendered frontend regression
that checks actual human-facing content, excluding debug JSON. Ubuntu runs the
existing no-model chart/OpportunitySet/comparison acceptance, then one real senior
ITUB4/BBDC4 comparison against an isolated candidate ASGI instance with the
existing runtime's actual provider/model configuration and production data.
Full senior responses stay in a private mode-0600 report on Ubuntu; public logs
contain coverage counts and timing only. There are no uploaded portfolio artifacts.
The candidate is not the loaded systemd process. A bounded timeout or failure
blocks checkout update; restart still requires existing system authentication.

Next quality work must close the deterministic ranking and financed-comparison
gaps, then inspect real output for specificity, contradiction analysis, actionability,
coverage, provenance and unknown handling. A comparison with direct ChatGPT
requires the same question and evidence; no superiority claim is made yet.

## Explicit Copilot stock comparison follow-up

A bounded grammar accepts only an explicit two-stock BUY comparison, e.g.
“Compare comprar ações ITUB4 e comprar ações BBDC4.” It produces the existing
structured UC-04 request and clears the unrelated sidebar selection for this
request. Structured form metadata wins; negated, three-asset, mixed-action,
option and monetary-budget questions do not match. Research mode, PIT cutoff
and original question remain intact. It does not infer monetary sizing.
The Ubuntu no-model gate now verifies this case produces two canonical
alternatives and excludes stale PETR4 selection. Shared Copilot output offers
an explicit button to open an existing canonical comparison centrally in
Strategy Lab, preserving the response snapshot without another request.
Opportunities' continuation pre-fills its selected ticker, but full AC-27/28
continuity of all objectives/restrictions and multi-leg orchestration remains open.

## Real results and structured reasoning follow-up

CI #1338 (d1ce0e6) and #1339 (f10bd48) passed Python, React and human-facing
render regression. Ubuntu run 37117816117 returned a real senior decision in
69.6 seconds, with 26 sources and five invalidation conditions. Run 37117965409
confirmed the no-model Copilot comparison and a senior response in 64.4 seconds.
Runtime metadata showed only the `reason` model stage, proving the deployed
configuration uses the existing single-synthesis branch: specialist findings
and committee conflicts are therefore absent by design. Input to reasoning was
~194k characters. Checkout updated but sudo restart was blocked; these are
candidate-instance results, not deployment of the new process.

To support this observed route, DecisionProposal now has backward-compatible
qualitative alternative_assessments. Each item separates supporting evidence,
contradicting evidence, decision implications, unknowns and references. The
schema and parser link IDs to actual supplied alternatives/assets and reject
foreign or duplicate IDs and malformed arrays. No financial metric, valuation,
probability or ranking authority is added. The workflow carries the structured
items and the shared frontend renders them. Ubuntu's senior gate requires both
canonical comparison alternatives and nonempty decision implications; merely
producing a generic proposal is no longer sufficient. This is coverage validation,
not proof that every interpretation is correct or superior to ChatGPT.

The final acceptance gate now executes one senior case for each screen and an
explicit Copilot comparison, each with a 240-second process bound and unchanged
production model configuration. It logs the configured provider/model identifier
(no credentials), context build timing and assessment coverage. For stock
comparisons, both canonical alternative IDs are required; asset analysis must
cover the supplied asset-evidence IDs. A failure prevents runtime checkout update.
The 20-minute workflow ceiling accommodates all four bounded cases plus CI
waiting; no production process or model routing is changed to make the gate pass.

Structured assessments are now required in the requested model schema whenever
canonical alternative/asset IDs are present; legacy requests without those IDs
retain the original schema shape. Every declared property remains required for
strict-schema client compatibility. Nonempty assessments without supplied IDs
are rejected as well as foreign and duplicate IDs. This hardens the admission
boundary; interpretations still require quality review against their sources.
