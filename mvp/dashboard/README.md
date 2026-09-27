# Dashboard V4 E2E

Read-only Streamlit interface for the frozen B3 V4 domain.

## Authoritative BTG input

For a BTG XLSX, portfolio positions come only from the `Renda Variavel`
sections `Posição > Ações` and `Posição > Opções`. Other statement sections
are not portfolio inputs. The statement end date is metadata for `as_of`.

The loader preserves broker identifiers. Portfolio Intelligence applies an
explicit economic identity resolver only when aggregating exposures and risk;
source fields are never silently rewritten.

## Current E2E path

BTG XLSX → `BtgRendaVariavelLoader` → `PortfolioContext` →
`DashboardE2EService` → Portfolio Intelligence + optional Options
Transactions + deterministic OpportunitySet → Streamlit.

The UI does not manufacture opportunities when analytical market/valuation/
options inputs are absent.

## Run locally

```powershell
cd C:\Users\Edmilson\Projects\b3-investment-options-agent
git switch feature/v4-dashboard-e2e
git pull
$env:B3_AGENT_PORTFOLIO_FILE = 'C:\Users\Edmilson\Downloads\022614697 (54).xlsx'
python -m pip install -e .
streamlit run mvp/dashboard/app.py
```

The current functional validation focuses on portfolio/options semantics before
connecting market/valuation inputs and the conversational orchestrator.
