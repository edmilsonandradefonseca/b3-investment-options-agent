# B3 Investment Copilot — Dashboard

## Purpose

O Dashboard é a camada de interação do B3 Investment & Options Agent. Ele apresenta dados e análises produzidos pelo backend e pelo Orchestrator, sem duplicar regras de investimento no React.

> Decision-support only. No order execution.

## Status atual

| Área | Estado |
|---|---|
| Portfolio | **IMPLEMENTADO** — snapshot BTG via Orchestrator |
| Options Intelligence | **IMPLEMENTADO** — transações/lifecycles/P&L determinísticos |
| Portfolio Intelligence | **IMPLEMENTADO** — exposição/capital/risk context |
| Opportunities | **PLACEHOLDER** |
| Copilot | **IMPLEMENTADO** — Golden Cases C01–C08 |
| Brokerage PDF ingestion | **IMPLEMENTADO** — parser + ledger SQLite + manifest |
| Reconciliação | **ENGINE BACKEND DISPONÍVEL**; UI dedicada ainda não implementada |
| Knowledge | **INDICADORES BACKEND**; UI dedicada ainda não implementada |
| RAG/Qdrant | Arquitetura preparada; não é dependência do Dashboard atual |
| Neo4j/Knowledge Graph | Arquitetura preparada; não é dependência do Dashboard atual |
| Execução de ordens | **NÃO IMPLEMENTADA / FORA DO ESCOPO** |

## Documentos

- [Architecture](./architecture.md)
- [Use Cases](./use-cases.md)
- [Testing](./testing.md)
- [Operations](./operations.md)
- [Upload Workflows](./upload-workflows.md)
- [Launcher](./launcher.md)

## Princípios

1. React é apresentação e interação, não fonte de verdade financeira.
2. Cálculos determinísticos permanecem no backend.
3. Orchestrator é a fronteira analítica das telas.
4. Uploads validam antes de substituir snapshots.
5. Proveniência e qualidade devem ser preservadas.
6. Ledger de corretagem não deve ser misturado silenciosamente ao Excel, evitando dupla contagem de P&L.
7. Implementar → Testar → Validar → Documentar/Fixar → Próximo bloco.

## Fluxo atual

```text
Usuário
   │
   ▼
React Dashboard / Vite
   │
   ├── POST /orchestrate
   ├── POST /imports/portfolio
   ├── POST /imports/options
   └── POST /imports/brokerage-notes
            │
            ▼
       FastAPI Server
            │
            ▼
     B3 Orchestrator
            │
       ┌────┼────┐
       ▼    ▼    ▼
   Portfolio Options Intelligence
    loaders   engines
       └────┬────┘
            ▼
    Structured response
            │
            ▼
        React UI
```

## Fonte de verdade

O comportamento do Dashboard e esta documentação devem permanecer versionados no GitHub. Ao retomar o projeto, este arquivo é o ponto de entrada; leia os documentos vinculados antes de alterar a arquitetura.
