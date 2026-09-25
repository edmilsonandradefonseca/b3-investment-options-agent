# Dashboard Launcher

Use the Dashboard as a single local application entry point.

From the repository root:

```powershell
.\dashboard.bat
```

Or directly from PowerShell:

```powershell
.\scripts\dashboard.ps1
```

The launcher:

1. starts the B3 Orchestrator on `127.0.0.1:8000` if it is not already running;
2. waits for `/health`;
3. starts the React/Vite Dashboard on `127.0.0.1:5173` if it is not already running;
4. waits for the Dashboard;
5. opens the Dashboard in the default browser;
6. keeps both processes under one launcher terminal;
7. stops only the processes started by the launcher when the launcher exits.

The React Dashboard continues to use the existing contract:

`React Dashboard → POST /orchestrate → B3 Orchestrator → workflow/deterministic engines`

No investment logic is duplicated in the launcher.

If the Orchestrator or Dashboard is already running, the launcher reuses it rather than starting another instance.

## Requirements

- Python environment with the project dependencies installed.
- Node.js/npm installed.
- Run from a checkout of the repository.

For a browserless start:

```powershell
.\scripts\dashboard.ps1 -NoBrowser
```
