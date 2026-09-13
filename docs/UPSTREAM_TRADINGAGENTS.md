# TradingAgents Upstream Reference

## Reference

- Repository: https://github.com/TauricResearch/TradingAgents
- Reference version: v0.4.2
- Branch: main
- Commit: be952b8eccb49720509af544c6675233bc1f10d0
- Commit message: Merge pull request #1310 from TauricResearch/v0.4.2
- Frozen on: 2026-09-13

## Purpose

The upstream TradingAgents repository is maintained inside upstream/TradingAgents/ exclusively as a reference implementation.

It is not part of the production architecture and must not be modified directly.

## Governance

The upstream reference is used to:

1. Study existing TradingAgents architecture and implementation.
2. Identify reusable concepts and components.
3. Compare design decisions with the B3 Investment & Options Agent.
4. Preserve a reproducible reference point.
5. Support controlled future integration.

## Important rule

Changes to upstream/TradingAgents/ are prohibited as part of normal development.

Any future upstream update must:

1. Be explicitly approved.
2. Record the new commit SHA.
3. Update this document.
4. Document relevant architectural differences.
5. Be validated before adoption.

## Integration principle

We will not copy or adapt upstream components automatically.

A component may be considered for integration only after reviewing:

- responsibility;
- interfaces;
- dependencies;
- data requirements;
- LLM usage;
- cost impact;
- look-ahead/data-leakage risk;
- impact on the B3 architecture;
- regression risk.

Architectural changes require an ADR.

## Relationship to our architecture

The B3 Investment & Options Agent is intentionally different from the generic upstream multi-agent framework.

Our approved architecture is:

Python-first → Local-first → LLM-for-reasoning

The upstream project is therefore treated as a reference and learning source, not as the architecture to be copied wholesale.
