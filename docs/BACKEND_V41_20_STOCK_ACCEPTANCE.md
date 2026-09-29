# B3 V4.1 — validação do backend com 20 ações

## Objetivo

Validar o backend antes da conclusão do React: rotas determinísticas, cotações
com origem e data, pesquisa UC-10 com DeepSeek local e escalações materiais ao
agente OpenClaw `b3-investment`. João Resolve compartilha infraestrutura, mas
seu scheduler e seus dados não são a autoridade do domínio B3.

## Execução no Ubuntu

Na branch `fix/react-portfolio-api`, em `/opt/b3-investment-options-agent`:

```bash
git pull --ff-only origin fix/react-portfolio-api
./.venv/bin/python -m pytest -q tests/test_fast_router.py tests/test_nightly_intelligence.py tests/test_intelligence_pilot_20.py
bash scripts/run_intelligence_pilot_20.sh 2
```

Se o piloto de dois ativos tiver roteamento, mercado e pesquisa válidos, rodar:

```bash
bash scripts/run_intelligence_pilot_20.sh 20
./.venv/bin/python scripts/summarize_intelligence_pilot_20.py
bash scripts/backend_full_validation.sh
```

O lote é sequencial, de baixa prioridade CPU e retomável no mesmo dia. A pasta
`/opt/b3-runtime/data/derived/intelligence_pilot_v41/` contém um JSON por
ativo e `latest.json`. O lote antigo em `intelligence_pilot_20/` é apenas
diagnóstico e não vale para este aceite.

## Critérios

- 20 ações distintas, cada uma com rota de mercado, UC-10/DeepSeek e senior/OpenClaw corretamente classificadas pelo Fast Router.
- 20 registros de mercado com origem e data até sete dias corridos.
- Pesquisa datada e pré-filtro material antes de DeepSeek; sem evento material, `skipped_no_material_events` e nenhuma chamada sênior.
- Cada dossiê DeepSeek concluído preserva referências de origem e é escalado ao agente OpenClaw isolado do B3. Resposta sênior só cita referências fornecidas.
- Pelo menos um caso real exercita DeepSeek e uma escalação OpenClaw. Sem evento material entre os 20, o resultado é `LIMITED`, não `PASS`.
- `backend_full_validation.sh` verifica transporte OpenClaw, runtime e serviços compartilhados. Conferir separadamente `/health`, `/portfolio/current` e a apresentação no React.

O relatório pode ser `LIMITED` por ausência de notícias materiais; forçar 20
inferências em cada LLM contrariaria a V4.1. Esta validação não certifica
ranking UC-03, análise fundamentalista institucional ou preço alvo. Esses
contratos precisam de um aceite próprio antes de declarar Opportunities pronta.
