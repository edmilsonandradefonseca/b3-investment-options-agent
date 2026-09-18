# ADR-0016 — Qdrant como primeira implementação do VectorStore

- **Status:** Accepted for MVP
- **Data:** 2026-09-17
- **Contexto:** RAG foundation

## Decisão

Usar Qdrant como a primeira implementação concreta do contrato `VectorStore`, inicialmente em ambiente local, mantendo o restante da aplicação independente do fornecedor.

O adapter `QdrantVectorStore` implementa somente:

- `upsert`
- `search`
- `delete`
- `count`

O adapter preserva no payload os dados necessários para provenance e filtros mínimos, incluindo `chunk_id`, `evidence_id`, conteúdo, source, timestamps, tickers, tópico, qualidade e lifecycle metadata.

## Por que Qdrant agora

O projeto já possui os contratos Evidence → Chunk → Embedding → VectorStore. Qdrant permite testar a infraestrutura real sem obrigar o projeto a adotar uma API específica no restante da arquitetura.

Para desenvolvimento local, o projeto fornece Docker Compose. Os testes usam o modo local em memória do cliente Qdrant e não dependem de um servidor externo.

## O que permanece aberto

- embedding de produção;
- política definitiva de hybrid retrieval;
- BM25/sparse retrieval;
- reranking;
- query rewriting;
- política definitiva de freshness + ranking;
- integração completa com `KnowledgeContext`;
- escolha de infraestrutura de produção.

## Segurança

O Qdrant local é infraestrutura de desenvolvimento. O compose não configura autenticação/TLS porque a intenção é uso local. Qualquer exposição além da máquina local deverá receber configuração explícita de segurança antes de ser considerada produção.

## Próximo passo

Subir Qdrant local, inserir um pequeno conjunto de evidências reais e testar consultas operacionais do dashboard. Os contratos serão ajustados somente quando os casos reais demonstrarem necessidade.
