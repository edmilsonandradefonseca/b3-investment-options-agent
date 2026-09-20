# Dashboard Operations

## Atualizar o checkout

```powershell
cd C:\Users\Edmilson\Projects\b3-investment-options-agent
git fetch origin
git pull --ff-only origin feature/mcp-mvp
git status
git log -1 --oneline
```

## Inicialização recomendada

Na raiz:

```powershell
.\dashboard.bat
```

URLs:
- Dashboard: `http://127.0.0.1:5173`
- Orchestrator: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`
- Version: `http://127.0.0.1:8000/version`

## Fluxo recomendado

1. carregar BTG Portfolio Excel;
2. carregar Options Transactions Excel;
3. abrir Portfolio;
4. abrir Options e clicar em Atualizar análise;
5. abrir Portfolio Intelligence;
6. testar Copilot;
7. carregar notas de corretagem.

## Nota de corretagem

O upload múltiplo é processado nota a nota.

Backend:
1. valida PDF;
2. grava temporariamente;
3. extrai texto;
4. calcula SHA-256;
5. move para `imports/brokerage_notes`;
6. grava no `options.sqlite3`;
7. registra `source_manifest.sqlite3`;
8. retorna `parsed_count`, `inserted_count` e IDs.

O ledger é idempotente.

## Encerramento

`Ctrl+C` na janela do launcher. Se o Windows perguntar se deseja finalizar o arquivo em lotes, responda `S` para encerrar os processos iniciados pelo launcher.

## Troubleshooting

### Backend
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### Upload funciona mas Options não muda

Isso pode ser esperado no estado atual: ledger de corretagem e snapshot Excel ainda são fontes distintas no runtime. Upload da nota não é prova de que o P&L da tela Options foi alterado.

### Artefatos locais

Não adicionar automaticamente:
- `frontend/node_modules/`
- `frontend/dist/`
- `frontend/playwright-report/`
- `frontend/test-results/`

## Regra de retomada

Ao voltar ao projeto, ler nesta ordem:

1. `docs/PROJECT_STATUS.md`
2. `docs/dashboard/README.md`
3. `docs/dashboard/architecture.md`
4. `docs/dashboard/use-cases.md`
5. `docs/dashboard/testing.md`
6. `docs/dashboard/operations.md`
7. `docs/dashboard/upload-workflows.md`

Depois ler o código/testes antes de alterar contratos.
