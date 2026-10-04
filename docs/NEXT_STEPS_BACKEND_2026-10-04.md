# Retomada backend — encerramento 03/10/2026 (UTC 04/10)

Branch: `feature/react-functional-v43-integration`. PR: #66, draft. Projeto Ubuntu: `/opt/b3-investment-options-agent`; serviço `b3-runtime.service`; dados `/opt/b3-runtime/data`.

## Current checkpoint — 2026-10-04

Backend timezone correction, tested installation, authenticated restart and active HTTP acceptance are complete. Run 37202797469 attempt 2 SUCCESS; active runtime revision a3dced7. The sequence below is retained as the original restart plan and has been executed. Next: implement the new React frontend against the approved functional specification and perform visual acceptance. Do not repeat the backend restart or production queue catch-up without a new reason.

## Original checkpoint (superseded by active acceptance)

| Bloco | Estado | Pendência |
|---|---|---|
| 1 Dividendos | Implementado e testado; ITUB4 19 eventos, BBDC4 12 mensais na validação | Corrigir dia de declaração no fuso São Paulo; cobertura BBDC parcial |
| 2 Preços-alvo | Parsers XP/Safra/Itaú/BTG e leitor qualificado implementados | Nenhum alvo BTG atual admitido; fonte inacessível mantém cobertura explícita |
| 3 Decisão econômica | BUY×BUY, Opportunities, conservação de caixa e síntese senior validados | Confirmar comportamento na API ativa após reinício |
| 4 Validar e ativar | 916 testes locais; CI e Ubuntu aprovados | Ajuste de fuso, ativação autenticada e conferência HTTP; novo React depois |

Run Ubuntu final: 37169879967 PASS. Fila real: run 37169940668, 10 READY, zero falhas/degradados/pendentes, 1095,9 s. Replay amplo: 37169879958, dividendos 148,8 s e notícias armazenadas 42,5 s. Isso não comprova frescor contínuo nem precisão semântica irrestrita.

Qwen dedicado: `qwen3:4b-instruct-2507-q4_K_M`, think=false, contexto 4096, saída 2048, temperatura 0, timeout 600 s, prompt v7. DeepSeek 8B continua disponível; roteamento global não foi trocado. Qwen prepara contexto opcional; Python calcula e OpenClaw/Luna realiza análise senior. Consumer observado a cada 15 minutos em dias úteis; aquisição noturna é separada.

## Sequência de amanhã

1. **Bloco 1, passo 4:** em `src/b3_agent/providers/bradesco_dividends.py`, substituir `observed_at.date()` pela data em `America/Sao_Paulo`. Testar o intervalo 00:00–02:59 UTC, garantindo que a declaração do próximo dia local ainda não seja anunciada. Preservar bruto ON/PN, datas e cobertura parcial.
2. **Bloco 4, passos 1–2:** executar regressão relevante e CI; verificar cobertura do novo provider no workflow Ubuntu, instalar a revisão testada e executar apenas validações justificadas pela mudança. Não repetir catch-up de produção já aprovado sem novos pendentes relevantes.
3. **Bloco 4, passo 3:** após instalar a revisão, reinício autenticado no Ubuntu: `sudo systemctl restart b3-runtime.service`. O runner usa sudo não interativo, que exige autenticação neste host. A autorização do usuário já existe; a senha não está disponível ao runner.
4. Confirmar na API systemd ativa: health, BBDC4 fonte RI/12 eventos/cobertura parcial, dividendos anunciados versus programados, BUY ITUB4×BBDC4 e Opportunities, sem consulta síncrona ao provider de dividendos. Registrar revisão, status e tempos sem segredos/dados privados nos logs.
5. Atualizar checkpoint e declarar o fechamento do escopo somente após a ativação. Depois iniciar novo frontend React pelas especificações salvas e validar visualmente.

## Limites preservados

Não criar ledger/tabelas que dupliquem SQLite/Parquet. Não inventar preço-alvo, data, probabilidade ou dividendo ausente. Não contornar HTTP403. Não tratar READY como auditoria semântica. Não declarar todos AC01–28 concluídos: Outcome/Experience/Learning pessoal ainda depende de ownership/configuração canônica; novo frontend ainda não foi iniciado.

## Active backend closure — 2026-10-04 09:41 America/Sao_Paulo

Block 1 step 4 and block 4 steps 1–5 are CLOSED for the scoped backend work. Corrected runtime revision: `a3dced7729f460187aaf44ba6a9809101bcc95d5`. Full local suite: 924 passed; CI run 37202675923 SUCCESS; Ubuntu focused regression: 21 passed. Authenticated service restart completed at 09:40:07 -03, PID 9790, after installation of the corrected provider.

Active HTTP acceptance: run 37202797469 attempt 2, job 111438148765 SUCCESS, `ACTIVE_PROCESS_AFTER_INSTALL=PASS` and `ACTIVE_BACKEND_CLOSURE=PASS`. Health returned HTTP 200. BUY ITUB4 × BBDC4: HTTP 200 in 2914.9 ms; stored dividends READ_OK with 19/12 events; qualified institution target counts 1/1. BBDC4 primary RI source, 12 monthly gross PN amounts and PARTIAL_MONTHLY_JCP_ONLY were asserted; scheduled unannounced events retained unknown announcement dates. Economic scenario comparison: HTTP 200 in 1498.6 ms. Opportunities: HTTP 200 in 1812.8 ms, two qualified institution target potentials. Both economic comparisons conserved cash; all focused interactive responses used zero LLM calls and stored dividend snapshots.

This validates deterministic active API behavior; no new senior synthesis or Qwen throughput benchmark was run. Earlier senior/worker acceptance remains separate evidence. No production queue catch-up was repeated. Reports remain private on Ubuntu. Scope closure does not certify all AC01–28, full complementary dividends, current BTG target coverage or Outcome/Experience/Learning ownership.

Next work: new React implementation and visual acceptance against `docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md` (document title V1.1 FINAL). Backend activation is complete; frontend work remains open.
