**Functional delivery plan — 02/10 (latest priority):**
Read `docs/DECISION_WORKSPACES_DELIVERY_PLAN_2026-10-02.md` before next code.
The user requires inside/outside-portfolio ranking, PUT risk/return comparison
and financed sell-to-buy alternatives (ASAI3/Embraer). UC-07/08/09 enrich these
flows; absent personal history must not block otherwise defensible current
analysis/ranking. AC-01…AC-25 are acceptance cases, not replacements for UC IDs.
This block implements existing B3 research before optional gap collection and
shared source/date presentation; full economic ranking remains open. Next block
is objective/constraint-aware economic comparison using existing contracts.
Do not restart completed storage inventories or prioritize new learning storage
over closing the decision workflows. Preserve UNKNOWN, PIT and V4.3.

**Registered storage gate complete — 02/10:**
Ubuntu installed `e816ef7`; registered-dataset metadata READ_OK, untruncated.
The registry declares only `market_data`, a Parquet directory partition for
ITUB4 (DIRECTORY_NOT_SCANNED). No business rows or Parquet columns were read.
Read the real registered-dataset acceptance in
`docs/UC08_CANONICAL_BOUNDARY_BLOCK_2026-10-02.md`. Together with the completed
known-SQLite schemas and repository adapter review, this leaves production
canonical Outcome/Experience/Learning ownership unconfigured in the inspected
scope; it does not prove global absence of unregistered storage.
Do not repeat inventories, scan this market-data directory or overload claims
and retrieval traces as a hidden learning ledger. Next implementation must
justify only essential canonical facts absent from existing owners, with atomic
outcome replay/version handling; real terminal and entry/PIT evidence remain
separate admission gates. Eligible outcomes remain zero.

**Canonical boundary block — 02/10:** read
`docs/UC08_CANONICAL_BOUNDARY_BLOCK_2026-10-02.md` first for commit-before-
projection/replay, typed PRE-ANALYSIS runtime composition, shared canonical
learning presentation and remaining owner/data gates. No new persistence or
real learning activation. User also supplied observed-lifecycle PASS at installed
`83e93d5`: 264 executions / 129 observed sequences / zero eligible outcomes.
Do not repeat completed validators or treat a typed injection hook as a deployed
canonical persistence adapter.

**Decision-history block — 02/10:** read
`docs/UC070809_DECISION_HISTORY_BLOCK_2026-10-02.md` first for the updated
matrix, candidate/contract evidence in Opportunities, Strategy Lab and Copilot,
exact-symbol identity, verification and completed focused Ubuntu gate. No canonical
learning/outcome is admitted from execution observations.
Ubuntu installed `53c5682`: exact decision projection and strict validation-time
cutoff PASS. Runtime now reports 264 option executions and 119 manifest rows;
XPBRJ100 has two executions, one observed sequence, zero eligible outcomes.
Read the real acceptance section; do not repeat this completed gate or infer
full account coverage/learning from the row counts.
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

# B3 Investment & Options Agent — avanços e retomada

> Atualização aditiva de 02/10/2026: código `bf71e65` publicado no mesmo PR/branch,
> CI [#1270 SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37001327561).
> A autoridade do registro de pausa abaixo permanece. Leia o novo bloco/matriz em
> `docs/UC070809_OBSERVED_LIFECYCLE_BLOCK_2026-10-02.md`: movimentos observados,
> proteção temporal e integridade de amostra nos serviços UC-08/09, sem novo ledger.
> Atualização real posterior de 02/10: Ubuntu atualizado para `d8423e4`; projeção
> observada e corte histórico estrito PASS conforme `Texto colado(9).txt`.
> Detalhes na seção Real Ubuntu acceptance do novo bloco. Desktop visual E2E e
> UC-07/08/09 integrais seguem abertos. Não repetir a validação concluída.

Data local da pausa: **01/10/2026, America/Sao_Paulo**, aproximadamente 21:38. No Ubuntu/GitHub, os registros em UTC já indicam 02/10. Retomada prevista: 02/10/2026 no horário local.

## Estado confirmado ao encerrar

- Repositório: `edmilsonandradefonseca/b3-investment-options-agent`.
- Branch: `feature/react-functional-v43-integration`.
- PR: [#66](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/pull/66), aberto, draft, não integrado.
- Último commit de implementação e instalado no Ubuntu: `8bc7cb9966626101c1303b8ed4c10f00296e0c23`.
- [CI #1268](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/36945695445): SUCCESS. A suíte Python completa passou localmente; CI verifica testes e build React.
- Este handoff e seu prompt são uma atualização documental posterior ao commit acima. Não representam código adicional instalado no runtime.
- O ambiente de desenvolvimento do assistente não é o Ubuntu de produção. As evidências reais abaixo vieram das saídas executadas pelo usuário.

## Autoridade e limites

Ler na retomada os seis documentos originais: `CHECKPOINT_B3_DECISION_INTELLIGENCE_2026-10-01.md`, `WORK_PROMPT_B3_INTELLIGENCE_REVIEW_2026-10-01.md`, `ARCHITECTURE_V4.3.md`, `USE_CASES_INVESTMENT_OPTIONS_V2.0.md`, `USE_CASE_ARCHITECTURE_TRACEABILITY_V2.0.md` e `FRONTEND_FUNCTIONAL_SPEC_V1.0.md`, todos em `docs/`. Este handoff atualiza o estado observado e não substitui a arquitetura.

Preservar: **Evidence before conclusion; Deterministic authority; Canonical Evidence authority; LLMs are not truth stores; OpenClaw/Luna never waits for DeepSeek; UNKNOWN remains UNKNOWN; Point-in-time correctness; Human-in-the-loop; No small-LLM router; Shared physical resources, isolated authority.**

Sem novas tabelas/ledgers por conveniência. Sem inferir assignment a partir de ausência de trades, covered CALL a partir de posições atuais, histórico de IV a partir de IV atual, ou underlying/strike/vencimento completo apenas pelo prefixo do símbolo. Sem multiplicador 100 presumido para as quantidades das notas.

## Avanços publicados

| Commit | Entrega | CI |
|---|---|---|
| `1568308` | Projeção histórica somente leitura; ligação com contexto de decisão; reutilização de histórico/modelo; telemetria; modo determinístico na API; caminhos opcionais de síntese | #1264 SUCCESS |
| `9fb8534` | Validador espera a API ficar pronta após restart | #1265 SUCCESS |
| `1cc05c2` | Histórico pessoal visível no AnalysisOutput/Copilot; Market Intelligence publica evidências conforme cada chamada termina | #1266 SUCCESS |
| `f54ce6f` | Cotação e cadeia atual OPLAB reutilizadas por 5 segundos; timestamps preservados; ausência de horário do provedor explícita | #1267 SUCCESS |
| `8bc7cb9` | Recuperação limitada de timeout de ações; validador mostra erro da API e verifica ação/cadeia separadamente | #1268 SUCCESS |

### Histórico e autoridade

`src/b3_agent/intelligence/personal_history.py` lê `option_transactions`, `transactions` e `source_manifest` com SQLite `mode=ro`, `query_only`, leituras limitadas e sem construtores que migram schema. Usa os tipos de transação e o serviço de reconstrução já existentes.

Compra/venda e fluxo de caixa são preservados conforme a fonte. Registros ambíguos, ordenação intradiária não conhecida, valores incompatíveis e possíveis duplicatas entre ledgers são sinalizados/excluídos. A reconstrução é isolada por corretora/símbolo, mas não prova cobertura completa de conta.

Uma sequência com saldo observado zerado é `OBSERVED_NET_FLAT_SEQUENCE`: saldo inicial ZERO_UNVERIFIED, desfecho econômico UNKNOWN e `eligible_for_learning=false`. Não é operação finalizada nem lucro total confirmado. Datas sem horário mantêm precisão DAY.

Consulta sem corte explícito: `RETROSPECTIVE_AS_LOADED`. Com `as_of` explícito: `STRICT_KNOWN_AT_TIME`; sem comprovação de disponibilidade/ingestão na data, registros não entram no replay. O manifesto real está ausente, portanto não há comprovação suficiente para replay de notas na base atual. O restante do contexto de mercado interativo continua atual; este mecanismo não transforma o workspace inteiro em replay histórico.

`GET /history/context` funciona sem modelos/provedores ou criação de tabelas. A projeção entra no contexto do LangGraph antes do reasoning e aparece nos workspaces. Isso não equivale a ligar experiências validadas a UC-08/09.

### Performance implementada

- Histórico: cache bounded/process-local, invalidação por revisão de SQLite/WAL, fingerprint, singleflight e cópias isoladas.
- LLM: reutilização bounded/process-local de entrada completa idêntica, instruções e schema dentro do mesmo cliente/modelo. Compactação de JSON por whitespace; não remove datas/evidências. Não garante HIT quando o contexto muda.
- Telemetria: latência por etapa e cache/input/output dos modelos; não há medição real de ganho no ciclo de agentes.
- Portfolio snapshots relidos a cada invocação, evitando manter carteira antiga capturada na configuração inicial.
- Mescla da resposta preserva precedência dos fatos determinísticos sobre chaves produzidas pelo senior.
- `context.analysis_mode="deterministic"` retorna contexto/fatos sem síntese senior ou João. A integração automática desse modo em duas fases para Opportunities/Strategy Lab ainda está aberta.
- `B3_WORKSPACE_SINGLE_SYNTHESIS=true`: opção para um reasoning senior no workflow de workspace, mantendo RiskValidator. Default `false`; não foi ativado/validado em produção.
- `B3_JOAO_SYNC_PERSPECTIVE=false`: opção para omitir a síntese extra síncrona de João mantendo recuperação de memória. Default segue compatível; não afirmar que foi ativado.
- OPLAB: cotação e cadeia PUT/CALL compartilhadas por até 5 segundos no processo; chaves isolam endpoint/ativo/credencial/transporte; preserva timestamps originais. Não armazena decisão ou carteira nesse cache.
- Opção sem `time` do provedor usa o timestamp real da coleta e flag `provider_timestamp_missing`; não usa o `as_of` arbitrário do chamador como observação de mercado.
- Ações: retry HTTP existente, timeout default 15s, duas tentativas por default; configurações existentes são respeitadas. Falhas transitórias não são cacheadas. Nenhum fallback para cotação antiga foi introduzido.
- DeepSeek permanece em background; Fast Router permanece code-only.

### Frontend

`PersonalHistory.tsx` mostra execuções, fontes, cobertura desconhecida, fluxo observado e amostra elegível; sem converter dados ausentes em taxas/probabilidades. AnalysisOutput é comum aos workspaces e Copilot.

Market Intelligence já fazia consultas paralelas, mas esperava todas terminarem para publicar preço/notícias/piloto. Agora publica cada resultado independentemente e consulta o histórico SQLite barato enquanto a síntese executa. Respostas atrasadas de outra seleção não substituem a inspeção mais recente. Sem nova chamada de orquestração duplicada. Não há ainda E2E visual real confirmando toda a mudança na versão desktop distribuída.

## Evidências reais: SQLite

Runtime ativo usa `/opt/b3-runtime/data`; checkout do usuário fica em `/opt/b3-investment-options-agent`.

A inspeção anterior já confirmou schemas/contagens e fez descoberta limitada de projeto/runtime/backups, sem erros/truncamento nessa descoberta. A validação da API reafirmou:

| Fonte consultada | Evidência |
|---|---|
| `options.sqlite3 / option_transactions` | READ_OK, 1 execução, sem truncamento |
| `b3_agent.db / transactions` | READ_OK, 0 linhas |
| `source_manifest.sqlite3` | Arquivo ausente |
| PETR4 / VALE3 / RENT3 | 0 execuções correspondentes nesta base |

A única execução identificada no diagnóstico: `btg-note:31718502:1:GGBRE221W2`, 04/05/2026, compra, quantidade 2500, preço 0,68, custo 1700. A cópia no diretório do projeto tinha a mesma identidade; não contar como outra operação. Pode ser uma recomposição/fechamento; não provar posição inicial zero.

Não foram encontrados PDFs/ZIPs de corretagem nos diretórios cobertos pela descoberta; foram encontrados arquivos XLSX de carteira. Isso não prova perda de dados nem ausência de notas em todo o host. A afirmação do usuário de que as notas completas já foram carregadas ainda não está reconciliada com as bases observadas.

`scripts/validate_personal_history_real.py`: **PASS real**. MISS: aproximadamente 1,67ms de processamento de histórico; HITs seguintes: aproximadamente 0,12–0,14ms. Esses números não são latência completa de workspace. O primeiro erro após restart foi conexão recusada; a espera por readiness resolveu a validação sem outro restart.

## Bloqueio OPLAB no encerramento

`scripts/validate_current_reuse_real.py --ticker VALE3`: **INCOMPLETE real**.

- Ação: HTTP 503; `oplab-stock request failed after 2 attempt(s): TimeoutError: The read operation timed out`.
- Cadeia: HTTP 503; `oplab request failed after 3 attempt(s): TimeoutError: The read operation timed out`.
- DNS no Ubuntu: `api.oplab.com.br` -> `136.248.75.21`.
- Curl normal e curl IPv4 direto sem proxy: HTTP 000, cerca de 15s, zero bytes de resposta.
- Curl verbose: TCP/443 conectado; TLS 1.3 e certificado válidos; ALPN HTTP/2; requisição enviada completamente; nenhuma resposta HTTP antes do timeout.
- O curl externo não enviou token. Os endpoints do runtime também falharam por timeout na requisição autenticada. Não concluir token inválido nem queda global da OPLAB.
- Uma tentativa de checagem DNS independente no ambiente do assistente não ficou disponível; não há confirmação externa do DNS/serviço.

A espera foi localizada após o envio da requisição, no caminho API/gateway a partir desse Ubuntu. Não há evidência para alterar DNS, certificados ou credenciais. **Não continuar aumentando timeout nem repetir todos os testes de rede.** Não afirmar cache OPLAB validado no runtime ou redução dos 80–95s dos agentes.

## Matriz atualizada antes do próximo bloco de código

Categorias usadas: fully implemented / implemented but not wired / missing implementation / missing real data / frontend-only gap. São classificações por capacidade, não conclusão de UC completo.

| Capacidade | Estado atual | Próximo requisito |
|---|---|---|
| Projeção das execuções SQLite existentes, somente leitura | fully implemented | Gate real PASS; manter cobertura UNKNOWN |
| Projeção pessoal -> contexto dos workspaces/reasoning | fully implemented, no escopo de projeção limitada | Não confundir com experiências/aprendizado validados |
| Execuções e limites no AnalysisOutput/Copilot | frontend-only gap resolvido no código/build | E2E visual/desktop real ainda aberto |
| Reconstrução genérica/serviços UC-07/08/09 existentes | implemented but not wired integralmente | Ligar somente entradas tipadas e desfechos comprovados |
| Expiração OTM, exercício/assignment, recompra e cadeia completa de rolls | missing implementation + missing real data | Evidência canônica independente, reconciliação e links de cadeia |
| Histórico completo pessoal, cobertura, IV/regime/cobertura na entrada | missing real data nos stores examinados | Reconciliar fontes carregadas sem criar outro ledger |
| PRE-ANALYSIS com FeatureSnapshot/MarketRegime e similaridade validada | implemented but not wired | Features PIT válidas; não fabricar snapshots |
| POST-OUTCOME / aprendizagem elegível | implemented but not wired integralmente | Outcomes finalizados, autoridade/persistência canônica existente, idempotência |
| Cache histórico / telemetry local | fully implemented | Gate real PASS no escopo histórico |
| Cache de aquisição OPLAB atual | fully implemented em código, missing real data/access na validação | API precisa responder; gate real INCOMPLETE |
| Reuso abrangente de histórico de mercado, chain, research e senior por contexto | missing implementation parcial | Fingerprints de evidência/as-of/ativo/carteira, invalidação e qualidade |
| Resposta determinística inicial em Opportunities/Strategy Lab | implemented but not wired no frontend | Evitar segunda coleta duplicada ao adicionar duas fases |
| Um senior por workspace | fully implemented como opt-in, não validado real | Comparar qualidade e latência; default compatível mantido |
| Seleção de strike/expiry e melhor risco-retorno | missing implementation parcial | Objetivo/capital/restrições explícitos; política determinística versionada |
| Frequência pessoal -> probabilidade de assignment de nova operação | missing implementation + missing real data | Separar frequência, expiry ITM modelado e exercício antecipado; delta não é probabilidade autoritativa |

## Próximos passos em ordem

1. **Retomar do GitHub atual.** Verificar HEAD/branch/PR/CI, ler este handoff, prompt de retomada, docs de autoridade e matriz anterior. Não restaurar código de branches antigas nem repetir implementação concluída.
2. **Tratar OPLAB como gate externo aberto.** Uma checagem limitada posterior pode verificar recuperação do provedor. Se persistir, registrar indisponibilidade e seguir com trabalho independente. Investigação adicional deve resolver uma hipótese nova concreta; não reexecutar a sequência de DNS/curl já registrada nem trocar tokens sem evidência.
3. **Reconciliar o histórico que o usuário diz já ter carregado.** Não varrer novamente os mesmos diretórios. Procurar evidência nova de origem/localização/status do lote, aproveitando ingestão e stores existentes. Se arquivos de origem/referência forem necessários, pedir somente a informação ausente. Não reingerir/migrar silenciosamente. Cobertura real é gate para validar resultados históricos pessoais.
4. **Completar UC-07 de forma aditiva.** Antes de código, mapear as entradas canônicas disponíveis para buy/sell, recompra, exercício, expiração e roll parcial/completo. Definir o que é observação, inferência/hipótese e UNKNOWN. Só persistir outcomes se finalizados e segundo os contratos existentes. Não converter as sequências observadas atuais em outcomes elegíveis.
5. **UC-08/09 -> UC-03/04/12.** Construir contexto tipado e determinístico com sample size/confidence/coverage, operações similares e learnings realmente elegíveis. Sem entrada IV/regime/PIT, indicar indisponibilidade. Validar PUT, CALL e ações, com evidência favorável e contrária.
6. **Performance abrangente.** Evitar recoleta entre fase determinística e síntese; reuso por fingerprint de ativo/as-of/carteira/evidência; research e retrieval limitados; invalidação por mudança de fontes/carteira. Prompts compactos sem remover contradições/limitações. Comparar full path versus one-senior opt-in com o mesmo contexto antes de alterar defaults. Medir coleta, SQLite, retrieval, modelos, total, cache HIT/MISS e execução física.
7. **Fluxos de decisão completos.** PUT uma semana versus um mês, escolha de strike sob restrições, covered CALL, BUY/HOLD/REDUCE/SELL ação, close/hold/roll option e comparações entre estratégias. Annualized premium sozinho não decide; manter ranking adiado quando entradas necessárias faltarem.
8. **Frontend E2E.** Validar exibição progressiva e histórico; conectar duas fases em Opportunities/Strategy Lab sem duplicar fontes; preservar datas, riscos, contradições, gaps e aprovação humana. Não reduzir todo o escopo a PUT.

### Gates de conclusão

Teste unitário/fixture e CI verde não substituem dados reais. Cada bloco deve ter escopo e limitações explícitos; só pedir um comando Ubuntu quando o bloco coerente estiver publicado e CI verde. As falhas externas não devem levar a taxas zero, preços estimados apresentados como fatos ou PASS artificial.

Não há comando obrigatório a executar nesta noite. O usuário encerrou o trabalho. Prompt pronto em `docs/RESTART_PROMPT_B3_INTELLIGENCE_2026-10-02.md`.

### Confirmação Ubuntu e UC-04 com cenários explícitos

O usuário confirmou que instalou `cb82c80` no Ubuntu e reiniciou
`b3-runtime.service`. Esta confirmação cobre o bloco anterior de research.

O incremento seguinte no Strategy Lab adiciona choques terminais explícitos sob
`terminal-price-scenarios-v1`, com P&L determinístico de ações, PUT cash-secured
e CALL coberta. A data comum precisa coincidir com o vencimento da opção para
expor seu payoff; mismatch ou dados essenciais ausentes ficam parciais. Choques
não são probabilidades, previsões, retorno esperado ou classificação.

Commit `f8f975f` foi publicado e o CI #1282 passou. O usuário ainda precisa
instalar o código e conferir a tela/cenário com contrato real. Leia
`docs/UC04_EXPLICIT_SCENARIO_COMPARISON_BLOCK_2026-10-02.md` para escopo,
equações, limites e aceite Ubuntu/UI pendente. A matriz funcional está em
`docs/DECISION_WORKSPACES_DELIVERY_PLAN_2026-10-02.md`. Próximo: B2, objetivos e
restrições comparáveis; depois C, ranking de Opportunities dentro/fora da
carteira. Completar custos/tributos e as duas pernas da rotação ASAI3→Embraer
segue aberto.

### Revisão funcional adicional e B2

A revisão mais recente confirma B1 como fundação e acrescenta dois gates de
produto, registrados na matriz: AC-27 preserva o contexto ao navegar
Opportunities→Market Intelligence→Strategy Lab; AC-28 prova orquestração pelo
Copilot de três alternativas com carteira/capital, duas cadeias e continuidade
para o Strategy Lab. AC-16 também exige estilo/termos de exercício confiáveis
para falar de assignment antecipado; sem isso, permanece `UNKNOWN`.

B2 acrescenta o objetivo explícito e opcional
`MAXIMIZE_WORST_CASE_RETURN_ON_CAPITAL`; default continua comparar sem ranking.
O serviço compara o pior retorno sobre denominadores declarados por alternativa
e só ordena se ambas tiverem payoff para todos os choques informados e capital
positivo conhecido. É uma política maximin sobre cenários escolhidos pela pessoa
usuária, sem probabilidade ou forecast. Opções multi-strike, P(ITM)/P(touch)/early
assignment separados, Opportunities ranking, alvos estruturados, sell-to-buy,
AC-27/28 e golden cases seguem abertos.

Este workspace não tinha mais o Python 3.14 temporário para executar a suíte após
reinicialização e não conseguiu baixar dependências pelo limite de rede. Fonte
Python compila, React/Vite build passa; regression tests adicionados devem ser
confirmados no CI do commit B2. Não pedir instalação Ubuntu antes do CI verde.

### B3A — comparação multi-strike PUT em Strategy Lab (CI verde; Ubuntu pendente)

O serviço e a tela agora comparam 2–20 contratos PUT selecionados por ID exato,
do mesmo ticker/vencimento, usando uma única cadeia corrente. Expõem bid/ask/mid,
spread, IV/Greeks, volume/OI, prêmio, break-even, colateral, perda máxima antes
de custos e choques explícitos. A política B2 pode calcular maximin somente
dentro dos choques e sobre colateral de strike conhecido.

P(ITM) e P(touch) são proxy lognormal não calibrado sob taxa/carry zero; IV ausente
ou ambígua deixa ambos UNKNOWN. Frequência pessoal UC-07/08/09 segue UNKNOWN.
Estilo de exercício aparece como campo reportado pela OPLAB, sem afirmar
verificação legal independente; assignment antecipado não é modelado. Não fecha
AC-15/16/17 sem cadeia real e aceite Ubuntu.

Bloco detalhado: `docs/UC04_PUT_CHAIN_COMPARISON_BLOCK_2026-10-02.md`.
Commit funcional final `b2fb05e`; CI #1287 SUCCESS: 796 Python tests e build
React. O sandbox não tem pytest nem dependências Python do projeto; os testes
foram executados pelo CI. Ubuntu permanece pendente. B1/B2/B3A devem ser
instalados juntos para o primeiro aceite real do Strategy Lab.


### Correção de preço de abertura em Options e transporte OpenClaw

Relatos do usuário em 02/10: a tabela Posições em aberto não mostrava o preço
unitário de aquisição/venda ao lado do preço atual; Opportunities (ITUB4) e
Strategy Lab (ITUB4 × WEGE3) falharam com `OSError [Errno 7] Argument list too
long` em `investment_synthesis`.

O prompt integral agora segue por stdin via `openclaw agent --message-file -`,
sem truncar fatos determinísticos, evidências ou UNKNOWN. Options exibe preço
unitário antes do preço atual e mantém o total das notas em coluna separada.
`Position.average_cost` tem precedência; na sua ausência, notas só atribuem
preço quando contrato, lado e quantidade conciliam exatamente. A nota PCARJ40,
C, 52.000 a R$ 0,02, total R$ 1.040,00, é o exemplo de aceite.

Sem custo canônico ou conciliação, preço permanece indisponível. Ver
`docs/OPENCLAW_STDIN_AND_OPTION_ENTRY_PRICE_BLOCK_2026-10-02.md`.


Commit `1be3283` publicado na branch/PR #66; CI #1289 SUCCESS (testes Python e
build React). Ubuntu permanece como gate de uso real para a coluna PCARJ40 e
os fluxos Opportunities ITUB4 / Strategy Lab ITUB4 × WEGE3. A correção não
altera o ranking determinístico nem admite execuções não conciliadas como custo.
