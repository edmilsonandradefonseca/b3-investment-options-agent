**Decision-history block — 02/10:** read
`docs/UC070809_DECISION_HISTORY_BLOCK_2026-10-02.md` first for the updated
matrix, candidate/contract evidence in Opportunities, Strategy Lab and Copilot,
exact-symbol identity, verification and focused pending Ubuntu gate. No canonical
learning/outcome is admitted from execution observations.
The user reports the preceding received-income feature working; do not repeat
its completed implementation or source analysis.

**Received-income block — 02/10:** the user supplied the BTG workbook and
authorized Portfolio dividend/JCP extraction. Read
`docs/BTG_RECEIVED_INCOME_BLOCK_2026-10-02.md` for the additive statement
projection, source semantics, verification and pending Ubuntu/desktop gate.
No new ledger or historical learning activation.

**New source checkpoint — 02/10:** the user confirmed `a0d0a2f` installed,
then supplied the brokerage-note ZIP. Read
`docs/BROKERAGE_BATCH_RECONCILIATION_2026-10-02.md` for the real audit,
additive parser/dedup correction, unsupported source types and pending Ubuntu
import gate. Do not overwrite the runtime database or repeat source discovery.

Continue o projeto B3 Investment & Options Agent no repositório `edmilsonandradefonseca/b3-investment-options-agent`, branch `feature/react-functional-v43-integration`, PR #66.

**Atualização da retomada de 02/10:** o bloco de código `bf71e654988811647d0a9a8d7c57a3b3e4938ff6`
foi publicado; CI #1270 SUCCESS. Leia também `docs/UC070809_OBSERVED_LIFECYCLE_BLOCK_2026-10-02.md`
antes de código: sua matriz e próximos passos atualizam a projeção UC-07 e os gates UC-08/09.
O usuário atualizou o Ubuntu para `d8423e4` e forneceu PASS real da projeção observada
e do corte histórico estrito em 02/10. Último instalado confirmado: `d8423e4`.
Leia a seção Real Ubuntu acceptance no novo bloco; não repetir implementação,
validação concluída, varredura de diretórios ou diagnóstico OPLAB. Cobertura completa
e UC-07/08/09 integrais continuam abertos.

Antes de alterar código, confirme branch/HEAD/PR/CI no GitHub e leia obrigatoriamente:

1. `docs/HANDOFF_B3_INTELLIGENCE_2026-10-01_END_OF_DAY.md`
2. `docs/CHECKPOINT_B3_DECISION_INTELLIGENCE_2026-10-01.md`
3. `docs/WORK_PROMPT_B3_INTELLIGENCE_REVIEW_2026-10-01.md`
4. `docs/ARCHITECTURE_V4.3.md`
5. `docs/USE_CASES_INVESTMENT_OPTIONS_V2.0.md`
6. `docs/USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md`
7. `docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md`
8. `docs/DECISION_INTELLIGENCE_REVIEW_2026-10-01.md`
9. `docs/PERSONAL_HISTORY_WIRING_2026-10-01.md`
10. `docs/CURRENT_PROVIDER_REUSE_2026-10-01.md`

Use estes documentos como autoridade e prossiga do estado atual, sem redesenhar o backend V4.3, restaurar branches antigas ou repetir trabalho concluído.

Estado confirmado ao pausar:
- Último código instalado no Ubuntu: `8bc7cb9966626101c1303b8ed4c10f00296e0c23`; CI #1268 SUCCESS. Um commit documental de handoff/prompt vem depois; verifique o HEAD atual.
- PR #66 aberto/draft, não merged.
- `/opt/b3-investment-options-agent` é o checkout; runtime ativo usa `/opt/b3-runtime/data`.
- Validação real da projeção histórica: PASS. `option_transactions` tem 1 execução, `transactions` tem 0 linhas, manifesto ausente; sem correspondências PETR4/VALE3/RENT3. Uma cópia da mesma execução não é outra operação. Cobertura UNKNOWN.
- Cache histórico funcionou: cerca de 1,67ms MISS e 0,12–0,14ms HIT. Isso não mede o ciclo completo dos agentes.
- Implementado: leitura SQLite somente leitura; histórico no contexto dos workspaces/Copilot; UI de histórico; publicação progressiva das evidências de Market Intelligence; reuso exato de LLM e telemetria; carteira relida por invocação; modo determinístico de API; one-senior opcional, default compatível.
- Implementado em código, NÃO real-validado: cache OPLAB de 5s para cotação/cadeia, preservando timestamps e separando credenciais/ativos. Validador real terminou INCOMPLETE: stock timeout após 2 tentativas; chain timeout após 3.
- Diagnóstico OPLAB já feito: DNS 136.248.75.21; TCP/443 e TLS/certificado válidos; curl IPv4 direto/sem proxy envia requisição HTTP/2 completa, mas não recebe resposta antes de 15s. Runtime autenticado também timeout. Não concluir token inválido ou queda global; não repetir essa sequência nem aumentar timeout sem hipótese nova.
- UC-07/08/09 completos, expiração/assignment/roll chains, IV/regime histórico, aprendizagem elegível e ranking econômico/probabilidade calibrada continuam abertos. Sample size elegível zero não significa zero perdas/assignments. Sequência net-flat não é outcome finalizado.

Preserve obrigatoriamente: Evidence before conclusion; Deterministic authority; Canonical Evidence authority; LLMs are not truth stores; OpenClaw/Luna never waits for DeepSeek; UNKNOWN remains UNKNOWN; Point-in-time correctness; Human-in-the-loop; No small-LLM router; Shared physical resources, isolated authority.

Continue autonomamente com os próximos passos do handoff. Antes do próximo código, atualize a matriz fully implemented / implemented but not wired / missing implementation / missing real data / frontend-only gap, e escolha a menor implementação aditiva que avance UC-07/08/09 -> Opportunities/Strategy Lab/Copilot. Não crie novas tabelas/ledgers por conveniência; aproveite os stores e contratos existentes. Reconcile a afirmação de notas já carregadas com a base limitada observada sem repetir varreduras ou presumir perda de dados.

Trate OPLAB como gate externo aberto, sem bloquear trabalho independente de dados live. Evite repetir coleta de market data, cadeia, histórico e research. Reuse contexto por fingerprint de ativo/as-of/carteira/evidência, com invalidação e telemetria. Compare qualidade e latência antes de ativar one-senior por default. Não anuncie ganho nos 80–95s sem medição real.

O padrão de análise deve servir PUT, covered CALL, ações BUY/HOLD/REDUCE/SELL, close/hold/roll e comparação de estratégias. Inclua fontes/as-of, spread/volume/OI, IV/Greeks quando presentes, DTE/moneyness, prêmio/preço efetivo, regime/eventos, carteira/capital/stress, operações pessoais similares, learnings com sample size/confidence, evidência contrária e limitações. Para VALE3 uma semana versus um mês ou escolha de strike, explicite objetivo/restrições; annualized premium e delta sozinhos não autorizam melhor strike ou probabilidade de assignment.

Publique mudanças coerentes na branch/PR, confirme CI verde e dê atualizações objetivas com commits. Só peça um comando de validação real no Ubuntu quando houver um bloco completo publicado e pronto. Não se limite a propor um plano: execute o trabalho autorizado até fechar o bloco e registre suas limitações.
