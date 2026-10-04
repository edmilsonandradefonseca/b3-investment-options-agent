Retome o B3 Investment & Options Agent e finalize o escopo do backend antes de iniciar o novo frontend React.

Repositório: edmilsonandradefonseca/b3-investment-options-agent. Branch feature/react-functional-v43-integration, PR #66 draft. Ubuntu /opt/b3-investment-options-agent, b3-runtime.service, dados /opt/b3-runtime/data. Use o runner já autorizado.

Leia primeiro docs/ARCHITECTURE_V4.3.md, docs/BACKEND_PENDING_CLOSURE_2026-10-04.md e docs/NEXT_STEPS_BACKEND_2026-10-04.md na versão atual do GitHub. Preserve as especificações funcionais salvas.

Estado: blocos 1–3 implementados; 916 testes e CI aprovados. Run Ubuntu 37169879967 PASS, mas sudo restart BLOCKED; testes candidate-ASGI não comprovam ativação HTTP. Fila real run 37169940668 terminou 10 READY, zero falhas/degradados/pendentes em 18,3 minutos. Não repita esse catch-up sem motivo.

Primeiro corrija a classificação de data de declaração em src/b3_agent/providers/bradesco_dividends.py: observed_at.date() usa UTC; usar America/Sao_Paulo e adicionar regressão na virada de dia. Valide, publique sobre o HEAD remoto atual e instale a revisão testada. Depois será necessário sudo systemctl restart b3-runtime.service autenticado e aceitação focada na API ativa para dividendos BBDC4, BUY ITUB4×BBDC4 e Opportunities. Não confunda checkout atualizado com processo atualizado.

Worker dedicado Qwen3 4B Instruct 2507 Q4_K_M, think=false, num_ctx4096, num_predict2048, temperatura0, timeout600, promptv7. Ele faz somente enriquecimento assíncrono, com saída estruturada e gate; Python é autoridade numérica e OpenClaw/Luna faz síntese financeira senior sem esperar Qwen. Não substituir roteamento global por acidente. Consumer observado a cada15min em dias úteis.

Preserve cobertura parcial dos12 JCP mensais BBDC4 e gross ON/PN, diferencie anunciado/programado/projetado. Existem registros qualificados XP/Safra/Itaú; parser BTG existe mas nenhum alvo BTG atual admitido. Não invente lacunas nem contorne403. Não duplique ledger SQLite/Parquet. READY não certifica todo conteúdo semântico. Outcome/Experience/Learning e todos AC01–28 não foram fechados.

Identifique bloco e passo em cada atualização, avance autonomamente nas ações autorizadas e avise quando o backend estiver efetivamente ativado. Só depois implemente o novo frontend React conforme as especificações salvas e faça conferência visual.
