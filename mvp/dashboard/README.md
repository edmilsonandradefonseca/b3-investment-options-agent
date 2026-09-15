# Dashboard MVP

Interactive Streamlit interface for the B3 Investment Copilot.

## Scope

- Load the real portfolio source configured by `B3_AGENT_PORTFOLIO_FILE`.
- Reuse `BtgRendaVariavelLoader` for BTG XLSX files.
- Reuse `PortfolioIntelligenceEngine` for deterministic intelligence.
- Provide portfolio table, distribution and exposure views.
- Read-only: no order execution and no investment decision generation by the UI.

## Run locally

```powershell
$env:B3_AGENT_PORTFOLIO_FILE = 'C:\Users\Edmilson\Downloads\022614697 (46).xlsx'
python -m pip install streamlit pandas
streamlit run mvp/dashboard/app.py
```

The next MVP increment will add Options, Opportunities, position drill-down and MCP/AI interaction without duplicating domain logic.
