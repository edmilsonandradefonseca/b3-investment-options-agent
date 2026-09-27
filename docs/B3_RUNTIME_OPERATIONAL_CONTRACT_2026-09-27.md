# B3 Runtime — Operational Contract (2026-09-27)

This document restores the operational contract defined by the 2026-09-21 practical guide and aligns it with the frozen V4 runtime.

## Responsibility

The Runtime is the infrastructure/lifecycle layer. It:

- prepares `/opt/b3-runtime`;
- starts and supervises the B3 Orchestrator process;
- waits for `/health`;
- records runtime/orchestrator PIDs;
- reports resources and shared-service reachability;
- is supervised by systemd.

It does **not** perform investment analysis, options strategy calculation, valuation, risk reasoning, LLM reasoning, LangGraph business orchestration or autonomous trading.

## Runtime paths

```text
/opt/b3-investment-options-agent   project code
/opt/b3-runtime                    operational root
/opt/b3-runtime/data               canonical operational data
/opt/b3-runtime/data/imports       imports
/opt/b3-runtime/data/parquet       parquet datasets
/opt/b3-runtime/logs               logs
/opt/b3-runtime/backups            backups
/opt/b3-runtime/runtime.pid        RuntimeManager PID
/opt/b3-runtime/orchestrator.pid   child Orchestrator PID
/etc/b3-runtime.env                deployment configuration
/etc/systemd/system/b3-runtime.service
/usr/local/bin/b3-runtime          CLI
```

## CLI contract

```bash
b3-runtime status
b3-runtime health
b3-runtime doctor
b3-runtime start
b3-runtime stop
b3-runtime restart
b3-runtime json
```

`status` answers whether the B3 environment is operational and reports runtime root, health, filesystem/SQLite/Parquet resources, shared services, bind address and process state.

`health` calls the Orchestrator `/health` endpoint.

`doctor` checks project/runtime resources, Orchestrator health and reachability of the shared embedding/Qdrant/Neo4j platform.

`start|stop|restart` delegate lifecycle supervision to `b3-runtime.service`.

## HTTP runtime status

```bash
curl http://127.0.0.1:8000/runtime/status
```

The endpoint exposes the same operational state through the B3 Orchestrator.

## Install / repair deployment

From the repository:

```bash
cd /opt/b3-investment-options-agent
git pull --ff-only origin main
bash scripts/install_b3_runtime.sh
b3-runtime start
b3-runtime status
```

The safe default bind remains loopback:

```text
B3_API_HOST=127.0.0.1
B3_API_PORT=8000
```

For the Windows 11 Tauri client on the same trusted LAN, explicitly install/configure the service with:

```bash
B3_API_HOST=0.0.0.0 bash scripts/install_b3_runtime.sh
b3-runtime restart
```

Then validate:

```bash
sudo ss -ltnp | grep ':8000'
curl http://127.0.0.1:8000/health
curl http://<UBUNTU_LAN_IP>:8000/health
```

Network/firewall exposure is a deployment concern. The Runtime does not add firewall rules.

## Shared AI platform alignment

The 2026-09-21 guide described Qdrant and Neo4j as disabled/optional. The current frozen V4 architecture has evolved: B3 consumes shared embedding, Qdrant and Neo4j services.

Runtime ownership remains unchanged:

```text
RuntimeManager -> observes shared services
RuntimeManager -X-> starts/stops/recreates shared services
```

The current shared defaults are:

- embedding: `http://127.0.0.1:8093`
- Qdrant: `http://127.0.0.1:6333`
- Neo4j: `bolt://127.0.0.1:7687`

Application data isolation and V4 ownership rules remain defined in `docs/V4_RUNTIME_INTEGRATION.md`.

## systemd

```bash
systemctl status b3-runtime
sudo systemctl restart b3-runtime
journalctl -u b3-runtime -n 100 --no-pager
```

systemd supervises the RuntimeManager. RuntimeManager owns the child Orchestrator lifecycle and waits for health before the runtime is considered healthy.
