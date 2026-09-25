# Dashboard Architecture

## 1. Arquitetura implementada

O Dashboard atual é React/Vite e conversa com um FastAPI local. O FastAPI traduz as requisições para o contrato do B3 Orchestrator.

```text
React Dashboard
      │ HTTP
      ▼
FastAPI — src/b3_agent/server.py
      │
      ▼
B3 Orchestrator / workflow
      │
 ┌────┼───────────────┐
 ▼    ▼               ▼
BTG  Options     Portfolio Intelligence
     engines
      │
      ▼
structured response
      │
      ▼
React UI
```

## 2. Componentes de software

### Frontend

Arquivo principal: `frontend/src/App.tsx`.

Responsabilidades:
- navegação;
- apresentação de snapshots;
- interação de Options;
- Copilot;
- uploads;
- status.

Não contém a lógica financeira principal.

### Launcher

- `dashboard.bat`
- `scripts/dashboard.ps1`

Inicia/reutiliza Orchestrator em `127.0.0.1:8000`, Vite em `127.0.0.1:5173`, aguarda health e abre o navegador.

### FastAPI boundary

Arquivo: `src/b3_agent/server.py`.

Contratos:
- `POST /orchestrate`
- `POST /imports/portfolio`
- `POST /imports/options`
- `POST /imports/brokerage-notes`
- `GET /health`
- `GET /version`

### Portfolio / Options

`BtgRendaVariavelLoader` valida o snapshot BTG.

`OptionsTransactionLoader` valida o snapshot de transações.

`OptionPerformanceEngine` calcula lifecycle/P&L.

### Brokerage

`BrokerageNoteParser` extrai transações das notas PDF.

`OptionTransactionLedger` persiste transações em SQLite com idempotência.

`SourceManifestRepository` registra fingerprint, origem, cobertura e metadados.

`OptionsReconciliationEngine` existe para comparar fontes e explicitar cobertura/possíveis duplicidades. Ele não deve fundir fontes silenciosamente.

### Copilot

O frontend envia `client=react-dashboard-copilot`, `surface=copilot` e `use_case_id`. A resposta é estruturada e depende do contexto determinístico/evidências.

## 3. Fontes de dados

### Operacionais hoje

```text
BTG Portfolio Excel → portfolio snapshot → Orchestrator → Portfolio

Options Excel → options snapshot → Orchestrator → Options
```

### Brokerage

```text
Brokerage PDF
   ↓
BrokerageNoteParser
   ↓
Option Ledger SQLite
   ↓
Source Manifest
   ↓
Reconciliation layer
```

A nota já é processada e persistida. Isso não significa que suas transações sejam automaticamente somadas às transações Excel no P&L. A consolidação canônica deve passar pela reconciliação.

## 4. Arquitetura-alvo versus implementada

A arquitetura visual do projeto inclui Orchestrator/LangGraph, agentes especializados, Obsidian, RAG/Qdrant, Knowledge Graph/Neo4j e APIs externas.

Esses elementos devem ser tratados como direção arquitetural quando ainda não estiverem no caminho operacional do Dashboard.

**Implementado no caminho atual:** React/Vite, FastAPI, Orchestrator, engines determinísticos, loaders, parser de corretagem, SQLite ledger, manifest, Copilot contract e CI/E2E.

**Evolução futura:** Opportunities UI, Knowledge UI, RAG/Qdrant operacional, Neo4j operacional, consolidação canônica do ledger no runtime, Tauri empacotado e dados externos em tempo real.

## 5. Governança

- Nenhuma credencial no frontend.
- Dados privados de carteira não devem ir para o repositório.
- LLM não é fonte da verdade numérica.
- Dashboard não executa ordens.
