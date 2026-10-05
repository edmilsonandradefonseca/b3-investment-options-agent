# NEXT STEPS — B3 V4 Runtime Integration

Use this file as the starting context for the next ChatGPT session.

## Immediate objective
Complete V4 Runtime Integration & Calibration after the verified functional freeze.

## Step 1 — Check PR #27
1. Inspect GitHub Actions for PR #27 / branch `feature/v4-runtime-integration`.
2. If CI is green and PR is mergeable, merge it routinely to `main`.
3. Verify post-merge CI on `main`.
4. Use the resulting main commit as the runtime-validation baseline.

## Step 2 — Locate or clone B3 repo on Ubuntu
Run first, without modifying anything:

```bash
echo "===== PROCURANDO B3 AGENT ====="
find ~ /opt -maxdepth 4 -type d -name "b3-investment-options-agent" 2>/dev/null

echo
echo "===== REPOS GIT RELACIONADOS A B3 ====="
find ~ /opt -maxdepth 5 -type d -name ".git" 2>/dev/null |
while read gitdir; do
    repo="$(dirname "$gitdir")"
    remote="$(git -C "$repo" remote get-url origin 2>/dev/null || true)"
    if echo "$remote $repo" | grep -qi "b3-investment-options-agent"; then
        echo "REPO:   $repo"
        echo "ORIGIN: $remote"
        echo
    fi
done
```

If nothing is found, clone the GitHub repository. Do not assume the B3 repo lives beside `joao-resolve`.

## Step 3 — Synchronize Ubuntu
After the repo location is known, synchronize to the verified runtime branch/main commit. Check `git status` before switching branches; do not discard local changes.

## Step 4 — Prepare infrastructure
Use only:
```
infra/docker-compose.yml
```
Do not use `infra/qdrant/docker-compose.yml` for the integrated V4 runtime; it is legacy/special-purpose and uses an unpinned Qdrant latest image.

Create local `infra/.env` from `infra/.env.example` if absent and set a non-default Neo4j password. Never commit credentials.

## Step 5 — Run the consolidated Ubuntu preflight
Use:
```bash
chmod +x scripts/runtime_preflight.sh
./scripts/runtime_preflight.sh
```

It validates:
- Docker / Compose;
- integrated Qdrant + Neo4j health;
- Python environment and project/dev dependencies;
- full pytest regression;
- Qdrant 768d hybrid collection creation;
- Neo4j connectivity and constraints.

Expected terminal markers:
```
QDRANT 768D HYBRID SMOKE OK
NEO4J SMOKE OK
===== RUNTIME PREFLIGHT PASSED =====
```

## Step 6 — Streamlit / real BTG acceptance
After preflight is green:
```bash
streamlit run mvp/dashboard/app.py
```
Validate the real BTG workbook using only Renda Variavel > Posição > Ações and Posição > Opções as authoritative position sources.

Known real validation reference:
- 21 stock rows
- 26 option rows
- 47 positions total
- stocks total previously matched R$ 1,544,171.52
- options total previously matched -R$ 130,854.87
- combined market value previously matched R$ 1,413,316.65
Do not commit the private workbook.

## Step 7 — Runtime/calibration sequence
After Streamlit smoke test:
1. Qdrant real-corpus hybrid retrieval benchmark.
2. Neo4j projection validation.
3. Canonical market/options/research provider adapters.
4. Historical transaction ledger ingestion/replay.
5. UC-01 through UC-12 real-data acceptance scenarios.
6. Factor/regime/retrieval/stress calibration.
7. Runtime-verified release candidate checkpoint.

## Important semantic invariants
- BTG snapshot cash is UNKNOWN unless separately supplied; never interpret missing cash as zero.
- LLM does not own deterministic facts.
- No invented opportunities.
- No autonomous order execution.
- PIT availability is mandatory.
- Correlation/significance != causality.
- Personal experience != market probability.
- Architecture V4 remains frozen unless ownership/topology/canonical contracts/human-decision boundaries change.

## Working mode
Advance autonomously in large coherent blocks. Use GitHub as persistent checkpoint. Stop only for a real Ubuntu/runtime test, unavailable private input/credential, meaningful architecture decision, or destructive action.
