# ADR-0015 — Contratos mínimos para Vector Store e Retrieval

- **Status:** Accepted
- **Contexto:** RAG foundation
- **Data:** 2026-09-17

## Decisão

Antes de escolher ou instalar um banco vetorial, o projeto fecha apenas contratos mínimos e provider-neutral:

1. `MetadataFilter` — filtros essenciais por ticker, tópico, fonte e tempo.
2. `VectorSearchResult` — resultado independente do fornecedor.
3. `VectorStore` — `upsert`, `search`, `delete` e `count`.
4. `RetrievalStrategy` / `VectorRetriever` — consulta textual convertida em embedding e delegada ao vector store.
5. `FreshnessScorer` — contrato simples para medir decaimento temporal, sem definir ainda uma política final de ranking.

## Não decidido ainda

- fornecedor definitivo do banco vetorial;
- modelo de embedding de produção;
- fórmula de ranking híbrido;
- BM25 ou outro sparse retrieval;
- reranker;
- query rewriting;
- ontologia adicional para RAG;
- integração definitiva com `KnowledgeContext`.

## Princípio

Os contratos devem ser pequenos o suficiente para serem alterados após os primeiros testes reais do dashboard e dos casos de uso. O banco vetorial é uma implementação de infraestrutura, não a definição da arquitetura de conhecimento.

## Point-in-time

O contrato já transporta filtros temporais, mas a política definitiva de filtragem e composição com lifecycle/freshness será validada quando houver dados reais. Dados determinísticos continuam authoritative.

## Próximo passo

Após CI verde, escolher e integrar um vector store local (candidato inicial: Qdrant) atrás de `VectorStore`, mantendo testes sem dependência externa.
