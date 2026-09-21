# Orchestrator ↔ MCP Memory Contract

## Purpose

Expose the existing B3 MCP memory tools through the B3 Orchestrator HTTP boundary so an AI client can use Obsidian as persistent project memory.

## Approved flow

```
AI Client / ChatGPT
        |
        v
B3 Orchestrator HTTP
        |
        v
B3 MCP memory tools
        |
        v
ObsidianKnowledgeStore
        |
        v
Windows Obsidian Vault
```

The Orchestrator does not implement memory logic. It delegates to the existing MCP tools:

- `write_memory`
- `search_memory`
- `read_memory`

## HTTP contract

### POST /memory/write

Request:

```json
{
  "path": "00_System/CHATGPT_MEMORY_TEST.md",
  "content": "# Test\n\nPersistent memory."
}
```

Response:

```json
{
  "status": "written",
  "path": "00_System/CHATGPT_MEMORY_TEST.md"
}
```

### POST /memory/search

Request:

```json
{
  "query": "CHATGPT_MEMORY_TEST"
}
```

Response:

```json
{
  "query": "CHATGPT_MEMORY_TEST",
  "matches": [
    "00_System/CHATGPT_MEMORY_TEST.md"
  ]
}
```

### POST /memory/read

Request:

```json
{
  "path": "00_System/CHATGPT_MEMORY_TEST.md"
}
```

Response:

```json
{
  "path": "00_System/CHATGPT_MEMORY_TEST.md",
  "content": "# Test\n\nPersistent memory."
}
```

## Governance

- Memory writes remain controlled writes.
- The Orchestrator delegates memory operations; it does not duplicate Obsidian storage logic.
- The MCP memory tools remain the authoritative memory boundary.
- No trading order execution is introduced.
- Empty paths, queries and content are rejected by the transport contract.
- Unknown request fields are rejected.
- The contract is covered by server boundary tests.

## Persistence acceptance test

The implementation is considered operational only after the following real-vault sequence succeeds:

1. `POST /memory/write`
2. `POST /memory/search`
3. `POST /memory/read`
4. Confirm the Markdown note exists in the configured Obsidian vault.
5. Repeat search/read from a new ChatGPT session.
