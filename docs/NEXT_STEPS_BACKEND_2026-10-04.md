# Retomada backend — encerramento 03/10/2026 (UTC 04/10)

Branch: `feature/react-functional-v43-integration`. PR: #66, draft. Projeto Ubuntu: `/opt/b3-investment-options-agent`; serviço `b3-runtime.service`; dados `/opt/b3-runtime/data`.

## Estado verificável

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
