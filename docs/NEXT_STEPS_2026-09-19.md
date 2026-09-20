# Próximos passos — Dashboard / Orchestrator

Data: 2026-09-19
Branch: `feature/mcp-mvp`

## 1. Estado confirmado ao final da sessão

- `pytest -q`: **PASSOU**.
- Os snapshots reais existem em `data/imports/`: `portfolio.xlsx` e `options_transactions.xlsx`.
- `load_active_snapshots()` foi validado diretamente: `portfolio_context` → `PortfolioContext`; `options_transactions` → 27 transações.
- O React foi compilado com sucesso anteriormente.
- A correção final adicionou `dashboard_snapshot` ao contrato `B3State`, permitindo que o estado produzido pelo LangGraph atravesse o workflow até o `OrchestratorResponse`.
- O backend já havia sido alterado para retornar explicitamente `result.dashboard_snapshot`.
- **Ainda falta a prova end-to-end final:** backend reiniciado + POST real em `/orchestrate` + React exibindo o snapshot real.

## 2. Primeiro passo amanhã — não alterar código antes deste teste

```powershell
git pull origin feature/mcp-mvp
python -m pytest -q
```

Depois iniciar:

```powershell
python -m uvicorn b3_agent.server:app --reload --port 8000
```

Testar `/orchestrate` diretamente. Critério de aceite: `result.dashboard_snapshot` deve conter `portfolio_context`, `portfolio_intelligence`, `options_transactions` e `options_performance`.

Só depois abrir/atualizar o React.

## 3. Validação funcional do Dashboard

Testar separadamente Portfolio, Options e Portfolio Intelligence. O objetivo é confirmar que os três módulos usam exclusivamente dados vindos do `/orchestrate`, sem cálculos de negócio duplicados no React.

## 4. Inconsistências técnicas identificadas

### 4.1 Dashboard duplicado

Existe uma implementação de Dashboard em `src/b3_agent/orchestration/runtime.py` e outra em `src/b3_agent/orchestration/workflow.py`.

A de `runtime.py` é a usada pelo endpoint Dashboard e calcula também Portfolio Intelligence e Options Performance. A de `workflow.py` retorna apenas portfolio_context e options_transactions.

**Ação:** decidir uma única fonte de verdade e remover/reutilizar a implementação duplicada. Não fazer isso antes do teste end-to-end.

### 4.2 Contrato B3State

Foi corrigido para incluir `dashboard_snapshot: dict[str, Any]`.

Amanhã criar teste explícito para impedir regressão e verificar as quatro áreas do snapshot.

### 4.3 Inferência CALL/PUT no React

`frontend/src/App.tsx` ainda possui `infer_b3_option_type()`, baseada apenas no último caractere do ticker.

Já corrigimos a regra B3 no backend para não classificar tickers como `PETR4` incorretamente.

**Ação:** o React não deve possuir regra de negócio para tipo de opção; deve consumir `option_type` produzido pelo backend/engine.

### 4.4 Responsabilidade do Dashboard

O Dashboard deve ser consumidor do contrato do Orchestrator, não uma segunda camada analítica. Evitar adicionar cálculo financeiro novo ao TypeScript.

### 4.5 `_configure_runtime` e cache

O server usa `lru_cache(maxsize=1)` e os imports chamam `cache_clear()`.

Validar se trocar os Excel e chamar novamente o Dashboard sempre produz o snapshot novo.

### 4.6 Health check

`workflow_configured` atualmente indica se `_configure_runtime` já foi executado/cacheado; não significa necessariamente que o workflow esteja saudável.

Avaliar amanhã se a semântica deve ser refinada.

### 4.7 Options filters

A tela possui filtros de ativo, tipo e datas, mas a consulta ainda não envia esses filtros ao backend.

Os filtros ainda não são um contrato real. Primeiro validar o snapshot completo; depois implementar filtros no Orchestrator, sem criar divergência no frontend.

## 5. Banco vetorial / Knowledge Graph

**Não instalar ainda.**

Sequência: estabilizar contratos → validar Dashboard → testar casos de uso → observar necessidades reais → escolher/adaptar banco vetorial e Knowledge Graph.

## 6. Ordem recomendada para amanhã

1. Pull da branch.
2. Rodar pytest.
3. Reiniciar backend.
4. Testar `/orchestrate` diretamente.
5. Confirmar `dashboard_snapshot`.
6. Testar Portfolio no React.
7. Testar Options.
8. Testar Portfolio Intelligence.
9. Corrigir somente problemas comprovados.
10. Reconciliar Dashboard duplicado em `runtime.py` e `workflow.py`.
11. Eliminar regra CALL/PUT duplicada do React.
12. Criar testes de contrato para o snapshot.
13. Só então avançar para os próximos casos de uso.
14. Banco vetorial permanece postergado.

## 7. Critério para considerar esta etapa concluída

`pytest PASS` + `/orchestrate` retorna snapshot real + React Portfolio mostra dados reais + React Options mostra transações/lifecycles reais + Portfolio Intelligence mostra resultado determinístico + nenhuma lógica financeira nova duplicada no frontend.

## 8. Regra de governança

Não fazer grandes refatorações amanhã antes de observar o comportamento real do Dashboard.

**provar → observar → corrigir → testar → consolidar.**