# React Windows Production Status — 2026-09-27

## Status

Production frontend baseline is on `main`.

Current main commits:
- `5304cb69a09ba73adc351e7da7aa817d5eefce47` — UC01-UC12 React/Tauri production workspaces.
- `c0397ff5891626c730c0bf9044bc865598b9ba40` — Windows application icon required by Tauri/NSIS.

Backend V4 remains frozen.

## Windows 11 application

```text
Windows 11
  -> Tauri 2 desktop shell
  -> React 19 + TypeScript + Vite
  -> configurable B3 backend URL
  -> frozen FastAPI backend/runtime
```

Validated GitHub Actions native build:

- Workflow: Windows Desktop App
- Run: `36347943659`
- Result: **SUCCESS**
- Runner: `windows-latest`
- Artifact: `b3-investment-copilot-windows`
- Artifact ID: `10941521833`
- SHA-256 artifact digest: `614375803f1fda4d58185e9e2bb4626178d976d07e8c2ac6f405c3eb6abc39d9`
- Installer: `B3 Investment Copilot_0.1.0_x64-setup.exe`

## UC coverage

```text
Overview
Portfolio                    UC-01
Options                      UC-02
Opportunities                UC-03
Strategy Lab                 UC-04
Market Intelligence
  Regime                     UC-05
  Factors                    UC-06
  Research & Events          UC-10
History & Learning
  Operations                 UC-07
  Learnings                  UC-08
  Similarity                 UC-09
Risk & Stress                UC-11
Copilot                      UC-12
```

## Runtime presentation invariants

The Windows frontend:

- does not reimplement investment calculations;
- renders frozen backend responses;
- exposes `UNKNOWN` rather than inferring absent values;
- exposes `LIMITED` / insufficient-history states;
- preserves `as_of`, quality/status and source references when supplied;
- has no autonomous order-execution controls;
- keeps the human as final decision authority.

## Next production gate — real instance

1. Install the generated x64 NSIS package on Windows 11.
2. Configure the reachable Ubuntu FastAPI URL in **Backend connection**.
3. Require `/health` to return OK.
4. Walk UC-01 through UC-12 against the real runtime and real portfolio/provider data.
5. Record UI-only defects without reopening backend architecture.

The backend URL is runtime-configurable and stored locally, so switching from localhost to the real Ubuntu instance does not require recompiling the Windows application.

If FastAPI is listening only on `127.0.0.1` on Ubuntu, it must be exposed safely to the Windows machine before the desktop client can connect. This is deployment/runtime configuration, not a V4 architecture redesign.
