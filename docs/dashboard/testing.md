# Dashboard Testing and Validation

## CI/Gates

O workflow `.github/workflows/dashboard-gate.yml` chama `dashboard-tests.yml` e cobre backend, build React e Playwright.

### Gate verificado

Commit: `8634847c470388fb1416ff47f7ad336d2fec8c97`

- CI #606: **SUCCESS**
- Dashboard + Copilot Gate #91: **SUCCESS**

A fixture PDF desse commit passou a ser realmente extraível por `pypdf`, usando o mesmo caminho de parsing do backend.

## Playwright E2E

Arquivo: `frontend/e2e/dashboard.spec.ts`.

### Teste 1
`dashboard reads BTG snapshot through orchestrator`

Verifica Portfolio, Options e Portfolio Intelligence através do Orchestrator.

### Teste 2
`dashboard upload buttons use orchestrator contracts`

Verifica upload de portfolio, options e brokerage PDF.

### Teste 3
`Copilot exposes all golden conversational cases and calls the orchestrator`

Verifica C01–C08, request de C01 e contrato `client/surface/use_case_id`. A resposta é mockada.

## Backend

Arquivo: `tests/test_dashboard_gate.py`.

Cobre dashboard contract, loaders, uploads, brokerage processing, rejeição de tipo incorreto, frontend boundary e snapshots ativos.

## Brokerage parser/ledger

Arquivo: `tests/test_brokerage_notes_and_ledger.py`.

Cobre parsing, BUY/SELL, data/número, persistência, idempotência e múltiplas transações.

## Próximos testes

1. PDF → Ledger → Reconciliation → Runtime → Options Dashboard.
2. Provar que Excel + nota não duplicam P&L.
3. E2E da futura tela de reconciliação.
4. E2E real de C01–C08 com workflow real.
5. Testes com conjunto controlado de arquivos reais anonimizados.

## Validação local

Preparar fixtures:

```powershell
$env:B3_AGENT_DATA_DIR="$PWD.ci-data"
python tests/e2e/prepare_dashboard_data.py
```

Iniciar:

```powershell
.dashboard.bat
```

Sem navegador:

```powershell
.scriptsdashboard.ps1 -NoBrowser
```

## Regra de evidência

Sempre separar:
- automated CI/E2E passed;
- manual validation performed;
- not yet validated.
