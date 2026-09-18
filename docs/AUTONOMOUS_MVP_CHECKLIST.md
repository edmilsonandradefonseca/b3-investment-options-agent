# Autonomous MVP Checklist

Branch: `feature/mcp-mvp`

## Priority

- [ ] Stock market → quant → existing valuation → stock opportunity integration
- [ ] Stock + options OpportunitySet assembly
- [ ] Deterministic reasoning context integration
- [ ] Dashboard integration with real OpportunitySet
- [ ] MCP exposure only for implemented backend capabilities
- [ ] Focused golden/regression tests for each integration

## Guardrails

- Never modify `main`.
- No trade execution.
- No LLM ranking.
- No invented valuation from market data.
- No direct external-data-to-decision path.
- Never claim tests passed unless they were actually executed.
- Preserve existing contracts and untracked/local user work.
