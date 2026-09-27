# React Production Frontend Foundation — 2026-09-27

## Status

Implementation branch: `feature/react-production-foundation`

Backend architecture remains frozen. This frontend phase consumes the existing FastAPI boundary without moving investment logic into React.

## Existing frontend inspected

Current production candidate stack:

- React 19
- TypeScript
- Vite
- Tauri shell already present
- `frontend/src/App.tsx` previously contained shell, routing state, API calls and transport contracts together.

Foundation refactor now separates:

```text
frontend/src/
├── api/
│   ├── client.ts
│   └── contracts.ts
├── app/
│   └── pages.ts
├── App.tsx
├── main.tsx
└── styles.css
```

## Real backend HTTP surface inspected

Source of truth: `src/b3_agent/server.py`.

| HTTP | Route | Typed client |
|---|---|---|
| GET | `/health` | `b3Api.health()` |
| GET | `/version` | `b3Api.version()` |
| POST | `/orchestrate` | `b3Api.orchestrate()` |
| GET | `/transactions?limit=` | `b3Api.listTransactions()` |
| POST | `/transactions` | `b3Api.addTransaction()` |
| POST | `/imports/portfolio` | `b3Api.importPortfolio()` |
| POST | `/imports/options` | `b3Api.importOptions()` |
| POST | `/imports/brokerage-notes` | `b3Api.importBrokerageNote()` |
| POST | `/imports/brokerage-notes/batch` | `b3Api.importBrokerageBatch()` |
| GET | `/imports/brokerage-notes/upload` | `b3Api.brokerageBatchUploadUrl()` |
| GET | `/analysis/live/{ticker}` | `b3Api.liveAnalysis()` |
| GET | `/research/news/{ticker}?limit=` | `b3Api.researchNews()` |

## Foundation decisions

- `VITE_B3_API_URL` is the canonical frontend base URL.
- Legacy `VITE_ORCHESTRATOR_URL` remains accepted temporarily as fallback.
- HTTP failures are normalized as typed `ApiError`.
- The shell uses URL hash routes without introducing a routing dependency in this first foundation slice.
- Navigation state is separated from transport logic.
- Existing UI remains desktop-first and preserves explicit empty states.
- React does not infer missing investment values and does not implement trading logic.
- Autonomous order execution remains absent.

## Validation

Repository CI already includes a Node 22 frontend job running:

```bash
cd frontend
npm install
npm run build
```

The implementation should be accepted only after that existing GitHub Actions frontend-build job passes on the pull request.

## Next implementation block

After foundation CI is green:

1. build screen-specific typed adapters/view-models for Portfolio and Options;
2. expose canonical backend response surfaces without duplicating engine logic;
3. add common `as_of`, quality, source/evidence and LIMITED/UNKNOWN presentation components;
4. wire Opportunities and Market Intelligence next;
5. then Risk/Scenarios, Historical/Learning and Copilot.
