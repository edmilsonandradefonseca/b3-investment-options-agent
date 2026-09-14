# Changelog

All material project changes are recorded here. Architectural changes must also have an ADR in `docs/ADR/`.

## [Unreleased]

### Valuation / Investment Price Policy
- Added deterministic Investment Price Policy after fair-value valuation.
- Accumulation Price uses Base Fair Value discounted by an explicit margin of safety.
- Reduce Price anchors to Base Fair Value.
- Sell Price anchors to Bull Fair Value.
- Current margin of safety is calculated from current price when supplied.
- Added ADR 0002 documenting the approved policy methodology.
- Added validation tests for thresholds, audit preservation and invalid inputs.

### Baseline
- Initialized the B3 Investment & Options Agent repository.
- Established the Python-first, local-first, LLM-for-reasoning architecture.
- Established component responsibilities and the normative LangGraph flow.
- Established C1–C7 change classification and mandatory impact review.
- Established the implementation roadmap from BASELINE through future EXECUTION.
- Established the rule: Implement → Test → Validate → Freeze → Next phase.
