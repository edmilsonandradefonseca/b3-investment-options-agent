> **Última atualização: 03/10/2026.** A seção final “Atualização autoritativa” prevalece sobre os estados anteriores.

# Checkpoint de sessão — B3 Investment & Options Agent

**Data local:** 02/10/2026 (America/Sao_Paulo)  
**Branch:** `feature/react-functional-v43-integration`  
**PR:** #66 (draft, aberto, mergeable)  
**Último HEAD de código validado:** `34c1fe6cb2669a7a115e17558dc4e3aa10c2698b`; este checkpoint será o commit mais novo da branch.  
**CI no HEAD:** sucesso — Actions run `37088394248` (Python e frontend build).

## Bloco funcional progressivo — 03/10/2026

Código `743de2d` + tabela `9256e0d`; CI #1334/#1335 SUCCESS: 806 testes Python e build React. Runner Ubuntu [37116668333](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37116668333) SUCCESS após aguardar CI verde.

### Entrega e matriz

| Capacidade | Estado deste bloco |
| --- | --- |
| Opportunities determinístico exposto à UI | Corrigido: workspace_result/candidatos/marketability/ranking e packs por ativo são expostos no resultado, mesmo sem fast route. Facts do fast route continuam prevalecendo. |
| Opportunities e Strategy Lab antes da síntese | Frontend solicita fatos determinísticos com research armazenado e zero modelos, publica-os e depois solicita o senior normal. Não repete pesquisa web na primeira fase. |
| Erro ou troca de seleção | Falha da síntese preserva o resultado determinístico já exibido; seleção/navegação invalida resposta antiga. Indicadores PENDING/FAILED explícitos. |
| Comparação lado a lado | Tabela alinhada de capital, métricas informadas pelo motor, qualidade, as_of e fontes. Não calcula no React nem atribui vencedor. Aceite visual ainda aberto. |
| UNKNOWN | Ausência de evidência de holding deixa “Na carteira” indisponível, não “Não”. Métricas ausentes não viram zero. |
| Copilot | Perguntas livres preservam caminho senior/contextual, sem serem forçadas a snapshot. Nenhuma nova orquestração transversal neste bloco. |
| Ranking econômico dentro/fora | Continua aberto; os 20 candidatos de PETR4 têm ordenação técnica, não ranking econômico validado. |
| Síntese/latência completa | Continua aberta. Não houve comparação de qualidade nem medição senior neste bloco. |

### Validação real e limites

A instância candidata isolada (ASGI) no runner usa o código GitHub e apenas configuração B3/provedores selecionada do processo real, sem imprimir valores de ambiente. Usa /opt/b3-runtime/data e os provedores reais. Sem fixtures/modelos/novos ledgers.

No primeiro gate, gráfico/PIT PETR4: 85 bars, timestamps de observação/disponibilidade dentro do cutoff, indicadores backend coerentes, zero opções; 357,4 ms. Opportunities: 20 candidatos, ranking DEFERRED_INCOMPLETE_CONTEXT, zero LLMs, 1.894,6 ms. Strategy Lab ITUB4 BUY × BBDC4 BUY: duas alternativas/packs, zero LLMs, 1.942,7 ms. Segundo gate do código final também PASS.

O checkout de produção foi atualizado pelo runner para `9256e0d`, mas o restart segue `RUNTIME_RESTART=BLOCKED` por sudo interativo. Os logs HTTP do processo ativo ainda têm o shape antigo de Opportunities. **Não declarar o backend novo ativado ou a UI Windows instalada.** O aceite PETR4 do processo ativo e o diferencial HTTP continuam PASS; isso não comprova carga do novo bloco. Nenhum sinal/process kill ou mudança de sudoers foi usado.

A primeira fase adiciona uma chamada determinística; caches de provedor existentes podem reutilizar aquisições dentro de suas regras, mas não há garantia de zero reacquisition ou melhora na latência total. O senior continua automático e não recebe fatos do cliente como autoridade. Cada resposta mantém seu próprio as_of/fontes; não fundimos snapshots distintos.

### Próximo bloco direto

1. Autenticar no Ubuntu e reiniciar `b3-runtime.service`; atualizar/rebuildar o frontend Windows da mesma branch. Este é o único bloqueio operacional do bloco novo.
2. Validar diretamente as telas reais: gráfico PETR4, candidatos antes do senior e comparação ITUB4 × BBDC4 no painel central. Não repetir inventários/histórico/Yahoo.
3. Fechar ranking econômico com política/objetivo/restrições explícitos sobre universo dentro/fora e aprofundar síntese/Copilot com um caso real por correção. UNKNOWN/PIT/V4.3/autoridade determinística permanecem obrigatórios; sem ledgers novos.

Fluxo autorizado simplificado: conferir código/HEAD no GitHub → bloco coerente + CI → candidato e serviço reais via runner. Informar progresso durante o trabalho e pedir ação humana apenas onde autenticação/UI local realmente impedir a execução.

## Aceite HTTP real após nova tentativa — 03/10/2026

Runner Ubuntu [37115180151](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37115180151): SUCCESS no checkout `e4b2594`. O sudo do runner permanece bloqueado, mas agora o workflow registra essa condição e consulta o processo ativo, permitindo validar um restart feito fora do job sem atribuí-lo ao runner.

- PETR4 HTTP PASS: 85 candles; último `2026-10-02T03:00:00Z`, fonte OPLAB; `source_refs=["b3_cotahist","oplab"]`; zero opções. Latência observada: 692,9 ms.
- Payload contém `price_history` e `quant`, além de latest/history_latest. Aceite visual do gráfico ainda não realizado.
- Diferencial determinístico: zero falhas de transporte/HTTP; não é aceite de qualidade econômica nem da síntese senior.
- Market Intelligence VALE3: orquestração determinística 1.217,5 ms; histórico direto 86 registros em 177,5 ms. Research armazenado sem eventos; pesquisa externa excluiu 18 registros futuros. UNKNOWN/limitações preservados.
- Strategy Lab ITUB4 BUY × BBDC4 BUY: resposta determinística em 1.737,9 ms, com contrato de comparação e evidências; não declara vencedor ou payoff sem entradas econômicas suficientes.
- Opportunities PETR4: resposta em 3.019,5 ms; ranking `DEFERRED_INCOMPLETE_CONTEXT`. Continua pendente ranking econômico dentro/fora da carteira.
- Todos esses workspaces reportam `derived_synthesis_status=NOT_REQUESTED`; os tempos não medem OpenClaw, qualidade de síntese ou ciclo completo.
- Relatório privado no Ubuntu: `/home/edmilson/.local/share/b3-investment-options-agent/live-validation/b3-deterministic-workspaces-20261003T100441Z.json`. Corpos de resposta e valores pessoais não foram publicados.
- Esta seção supersede a pendência HTTP da tentativa anterior. Nenhum restart manual adicional é necessário para esse aceite. Gaps funcionais e aceite visual permanecem abertos.

## Retomada real pelo runner Ubuntu — 03/10/2026

- HEAD recebido: `5e3815b`; CI #1329 SUCCESS; PR #66 continua aberto/draft.
- Commit `39329e6` adiciona ao workflow Ubuntu atualização fast-forward do checkout de produção, restart não interativo, readiness e aceite HTTP de PETR4 antes do diferencial determinístico.
- Runner `ubuntu`, run [37114876417](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37114876417), comprovou atualização de `/opt/b3-investment-options-agent` de `4db5b07` para `39329e6`.
- **Restart bloqueado:** `sudo: interactive authentication is required`. Nenhuma tentativa de contornar autenticação, alterar sudoers ou terminar o processo do serviço foi feita.
- Aceite HTTP, gráfico em runtime e diferencial foram SKIPPED por dependência desse restart. O checkout atualizado não comprova que o processo ativo carregou a correção.
- CI #1330 [37114878300](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37114878300): testes Python e build React SUCCESS. O workflow de aceite Ubuntu falhou no restart; não confundir com CI de regressão.
- Próximo desbloqueio mínimo no terminal Ubuntu: `sudo systemctl restart b3-runtime.service`. Após autenticação, executar o aceite HTTP do checkpoint antes de avançar às telas.
- Revisão estática confirmou gráfico consumindo série do backend e os gaps documentados de ranking, comparação financiada e orquestração; não equivale a aceite visual ou entrega dessas funções.
- Preservados V4.3, UNKNOWN, autoridade determinística, PIT e os stores existentes. Nenhuma mudança funcional ou ledger novo nesta retomada.

## Estado ao encerrar

O usuário atualizou o Ubuntu até `4db5b07`, reiniciou `b3-runtime.service` e consultou `/analysis/live/PETR4`. A resposta teve `history_count=80`, último candle COTAHIST em `2026-09-25`, `source_refs` incluindo `oplab` e `options_count=0`. Isso revelou que OPLAB estava sendo buscado, mas os candles não entravam no histórico elegível da rota.

## Diagnóstico e alterações desde o último bloco

- O adaptador consultava o intervalo remoto descoberto apenas se a data final fosse dia útil. Corrigido para consultar também em fins de semana; teste de regressão adicionado.
- A rota `/analysis/live/{ticker}` capturava `as_of` antes da aquisição. O OPLAB marca `available_timestamp` no momento da ingestão, posterior ao início da chamada, então o próprio corte descartava esses candles. Corrigido para registrar o corte depois da aquisição. Observações ainda futuras em relação ao corte continuam excluídas.
- Teste da rota cobre candle recebido depois do `as_of` inicial e rejeita registro com observação futura.
- CI final no HEAD `34c1fe6`: sucesso. O runner Ubuntu executou o caminho contra `/opt/b3-runtime/data` no commit do código `cb141dc`: PETR4, ITUB4, BBDC4 e WEGE3 tiveram 85 candles combinando `b3_cotahist` + `oplab`, até `2026-10-02`, em 145–181 ms. Nenhuma cotação atual ou cadeia de opções foi solicitada. É uma validação direta do serviço de histórico, ainda falta validar a resposta HTTP da rota com o último commit instalado.

## Avaliação do piloto Yahoo Finance

O piloto `yfinance` é somente de leitura, não persiste dados e não foi integrado à aplicação. No runner, obteve dados até 02/10 em aproximadamente 226–601 ms. A comparação com COTAHIST encontrou diferenças por ativo/período: VALE3 teve apenas 45 dias sobrepostos e mediana de diferença de fechamento de 0,766%; ITUB4 teve divergências pontuais de até 2,913%; PETR4, BBDC4 e WEGE3 tiveram melhor concordância geral, mas também pontos discrepantes. Não usar Yahoo sem validação específica como fonte de preço, indicador determinístico, liquidez, opção, aprendizado ou decisão. O histórico OPLAB recente foi obtido no runner, então Yahoo não é necessário para preencher a lacuna atual.

## Próximo passo — aceite HTTP no Ubuntu

O serviço em produção ainda não recebeu o último commit `34c1fe6`. Amanhã, atualizar e reiniciar:

```bash
cd /opt/b3-investment-options-agent &&
git pull --ff-only origin feature/react-functional-v43-integration &&
sudo systemctl restart b3-runtime.service

ready=0
for i in {1..20}; do
  if curl -fsS --max-time 2 http://127.0.0.1:8000/health >/dev/null; then
    ready=1
    break
  fi
  sleep 2
done
test "$ready" -eq 1 &&
curl -fsS --max-time 15 http://127.0.0.1:8000/analysis/live/PETR4 |
./.venv/bin/python -c 'import json,sys; d=json.load(sys.stdin); m=d["market"]; print({"ticker":d["ticker"],"history_count":m["history_count"],"latest_source":m["latest"]["source"],"latest_date":m["latest"]["observation_timestamp"],"sources":d["source_refs"],"options_count":d["options"]["contract_count"]})'
```

Resultado esperado: último candle em `2026-10-02`, fontes `b3_cotahist` e `oplab`, histórico por volta de 85 candles e `options_count=0`. Se a resposta continuar em 25/09, inspecionar no payload a `available_timestamp` dos registros OPLAB e o `as_of` retornado antes de fazer outra alteração.

## Trabalho ainda aberto

- Validar visualmente Market Intelligence/PETR4: série, indicadores determinísticos, fontes, `as_of` e aviso de cobertura parcial.
- Retomar o objetivo principal de Opportunities, Strategy Lab e Copilot com casos reais e logs privados já existentes, sem repetir os diagnósticos de timeout/ausência anteriores.
- Opportunities ainda precisa evidenciar candidatos realmente calculados dentro e fora da carteira e uma ordenação econômica justificável; não declarar resolvida a venda de uma ação para financiar outra.
- Strategy Lab ainda precisa demonstrar comparação lado a lado de BUY de ações e distinguir métricas determinísticas de cenários. Não declarar vencedor quando os dados ou política não sustentarem.
- Market Intelligence deve apresentar cotação/histórico/indicadores/notícias com data, fonte, proveniência e limitações, sem preencher lacunas por inferência.
- Para UC-07/08/09, manter resultados observados separados de outcomes canônicos; `UNKNOWN` não vira zero. Learning/ranking só após evidência canônica suficiente e corte PIT estrito. Não criar ledgers por conveniência.
- Corrigir/validar erros comuns de síntese OpenClaw nos workspaces e comparar latência por estágio. O último gate extenso mostrou timeouts em Opportunities, Strategy Lab e Copilot; não repetir o replay longo inteiro sem correção focada.

## Restrições e documentos de autoridade

Preservar V4.3, autoridade determinística, `UNKNOWN`, proveniência e correção point-in-time. GitHub branch/PR é fonte da implementação. Antes de mudanças amplas, ler `docs/RESTART_PROMPT_B3_INTELLIGENCE_2026-10-02.md`, `docs/HANDOFF_B3_INTELLIGENCE_2026-10-01_END_OF_DAY.md` e documentos de autoridade que eles indicam, especialmente:

- `docs/DECISION_WORKSPACES_DELIVERY_PLAN_2026-10-02.md`
- `docs/UC070809_PRODUCTION_GAP_ANALYSIS_2026-10-02.md`
- `docs/UC070809_OBSERVED_LIFECYCLE_BLOCK_2026-10-02.md`
- `docs/UC070809_DECISION_HISTORY_BLOCK_2026-10-02.md`
- `docs/UC08_CANONICAL_BOUNDARY_BLOCK_2026-10-02.md`

## Prompt para retomar amanhã

> Continue o projeto B3 Investment & Options Agent no repositório `edmilsonandradefonseca/b3-investment-options-agent`, branch `feature/react-functional-v43-integration`, PR #66. Leia primeiro `docs/SESSION_CHECKPOINT_B3_INTELLIGENCE_2026-10-02.md`, depois `docs/RESTART_PROMPT_B3_INTELLIGENCE_2026-10-02.md`, `docs/HANDOFF_B3_INTELLIGENCE_2026-10-01_END_OF_DAY.md` e documentos de autoridade indicados. Confirme HEAD e CI no GitHub. O último HEAD de código validado é `34c1fe6` e seu CI está verde; o checkpoint documental foi gravado após esse commit. Confirme o HEAD e CI atuais no GitHub. O Ubuntu ainda está em `4db5b07`: o endpoint mostrou 80 candles até 25/09 embora `source_refs` incluísse OPLAB. A correção publicada captura o `as_of` após adquirir o histórico para que `available_timestamp` de ingestão passe no corte sem admitir observações futuras. Primeiro peça/analise a validação HTTP Ubuntu descrita no checkpoint. Se passar, confirme visualmente Market Intelligence/PETR4. Depois continue a implementação real para Opportunities, Strategy Lab e Copilot a partir dos gaps registrados: ranking econômico dentro/fora da carteira, comparação BUY financiada/métricas, dados e painéis exigidos, síntese/latência. Não redesenhe V4.3, não crie ledgers, preserve UNKNOWN, autoridade determinística e PIT. Trabalhe autonomamente, mantenha CI verde e só solicite validação Ubuntu quando o próximo bloco completo estiver pronto.

## Atualização autoritativa — 03/10/2026: qualidade estruturada e routing

Código validado: `2d18f510c789cf18e9839583a774333199e49eea`.
CI #1342 [SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37118672441): **820 testes Python**, React build e regressão de renderização visível.
Runner Ubuntu [37118669518 SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37118669518).
O commit que registra esta seção é documental, posterior ao código validado.

### Entrega e causas comprovadas

- Interface descartava achados/riscos/referências dos especialistas, conflitos do comitê, custo de oportunidade, impacto no capital, confiança e invalidações da proposta. Agora todos chegam à saída compartilhada das três telas/Copilot; capital incremental ausente não aparece como zero.
- Síntese de workspace usa por padrão o caminho direto existente (`B3_WORKSPACE_SINGLE_SYNTHESIS=true`); a instância real confirmou somente o estágio `reason`. Não esperar campos de três especialistas/comitê nesta configuração. O contrato agora produz análise qualitativa estruturada **por alternativa/ativo**, com evidências favoráveis/contrárias, implicações, lacunas e referências. IDs inexistentes/duplicados e arrays inválidos são rejeitados; a análise é obrigatória no schema quando há IDs fornecidos.
- Prompts agora exigem análise específica, contraditório, critérios de invalidação observáveis, lacunas proporcionais e português. Não criam métricas financeiras, preço-alvo, probabilidades ou ranking.
- Copilot aceita uma gramática limitada de comparação explícita de duas compras de ações e usa o composer UC-04 existente, excluindo seleção lateral obsoleta. Formulários estruturados têm prioridade. Perguntas negadas, três ativos, opções, ações mistas ou orçamento monetário não são adivinhadas. A comparação retornada pode ser aberta centralmente no Strategy Lab preservando o snapshot. Continuidade integral AC-27/28 segue aberta.

### Aceite real deste bloco

Instâncias ASGI candidatas usaram os dados de produção e configuração real do processo Ubuntu, sem fixtures. Todas retornaram HTTP 200, nenhuma API error e os IDs esperados:

| Jornada | Tempo desta execução | Análises estruturadas | Fontes |
| --- | ---: | ---: | ---: |
| strategy_lab_stock_buy_comparison | 44.3 s | 2 | 26 |
| opportunities_petr4 | 89.7 s | 1 | 32 |
| market_intelligence_vale3 | 73.1 s | 1 | 20 |
| copilot_natural_language_compare | 89.8 s | 2 | 26 |

Provedor/modelo **solicitados na configuração**: OpenClaw / `openai/gpt-5.6-luna` em todas as jornadas. Não há roteamento dinâmico para modelo mais avançado neste bloco; identificar modelo solicitado não é verificar internamente a versão executada pelo gateway.
Context build: 19–50 s; síntese senior: 23–43 s; inputs ~82–364 mil caracteres. Não atribuir toda latência ao frontend nem alegar melhoria global de tempo a partir de execuções variáveis.
Relatórios completos ficam privados, mode 0600, no Ubuntu; logs públicos mostram apenas metadados.

PETR4: 85 barras, PIT observation/availability <= as_of, quant data_points igual à amostra, zero opções. HTTP ativo também preservou aceite até 02/10, fontes COTAHIST/OPLAB e zero opções. Determinístico: Opportunities 20 candidatos técnicos ~1,6 s; comparação ~1,6 s; Copilot explícito PASS sem modelos e sem PETR4 obsoleto.

### Estado de implantação e próximo trabalho

Checkout `/opt/b3-investment-options-agent` atualizado para código validado. **Processo systemd ainda não confirmado nessa versão**: `sudo -n systemctl restart b3-runtime.service` permanece bloqueado por autenticação interativa. A última confirmação de reinício do usuário precede este novo bloco. Para ativar: executar `sudo systemctl restart b3-runtime.service` e atualizar o frontend dessa branch na instalação Windows. Não confundir CI/candidato/checkout com tela ou processo carregado. Após o reinício, verificar uma resposta senior HTTP com `proposal.alternative_assessments` e a renderização central, sem repetir quatro chamadas longas sem necessidade.

A missão completa continua aberta. Prioridades seguintes: política determinística de ranking econômico e universo dentro/fora da carteira; fontes estruturadas de alvos/valuation; comparação financiada sell-to-buy com capital/custos; orquestração multi-alternativa AC-27/28; qualidade semântica e comparação controlada com ChatGPT usando a mesma pergunta/evidência. Cobertura estrutural não comprova superioridade, qualidade de cada inferência ou aceite integral dos AC-01–AC-28. UNKNOWN, V4.3, PIT e nenhuma nova ledger preservados.

Detalhes: `docs/INTELLIGENCE_QUALITY_CAUSES_2026-10-03.md`.


### Reinício confirmado no processo ativo — 03/10/2026, 09:14 BRT

Usuário informou “feito”. Validação [37122133861 SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37122133861), usando o runner Ubuntu **somente por HTTP contra o serviço systemd ativo**, sem ASGI candidato, git update, sudo ou outro reinício:

- `/analysis/live/PETR4`: 85 barras, último registro 02/10, fontes COTAHIST/OPLAB, zero opções.
- Copilot explícito ITUB4/BBDC4: HTTP 200, sem erro, duas alternativas canônicas e duas `proposal.alternative_assessments` com IDs exatos e implicações por alternativa; 26 fontes; 82,4 segundos.
- Seleção lateral PETR4 foi excluída: asset_evidence contém exatamente ITUB4 e BBDC4; workspace Strategy Lab.
- CI do commit de validação `2e4a0d5` SUCCESS. Backend validado anteriormente `2d18f51` não foi alterado por esse commit (somente workflow de verificação).

**Este aceite substitui o estado “reinício pendente” do bloco anterior.** O novo contrato está confirmado no processo ativo. Não confirma visualmente a instalação Windows nem qualidade semântica superior ao ChatGPT. Ranking econômico amplo, alvos/valuation verificados, comparação financiada e AC-27/28 completos continuam como próximos blocos. Não repetir as quatro chamadas senior nem pedir outro reinício sem nova mudança de runtime.


## 2026-10-03 — observed Opportunities screen accepted on candidate Ubuntu

Code `ad0f738f7e1624749103bd3db3162e2f666eb2fb`. GitHub CI run 37125688641 SUCCESS: 829 Python tests, React build and SSR decision rendering regression. Real self-hosted Ubuntu run 37125685987 SUCCESS: new explicit stock screen validated against actual production providers and portfolio, then one actual senior request.

Both observed objectives returned PARTIAL_COMPARABLE_UNIVERSE: VALE3 had 86 records and a different observation window, while RENT3/VIVT3/BBAS3 had 85 and a common window. Three assets ranked; VALE3 visibly excluded from ordering, still retained in comparison/senior interpretation. Deterministic requests: 3.67s risk and 2.67s liquidity; zero LLM calls. Senior: HTTP 200, no API error, four alternative assessments with implications and unknowns, 81.15s. This is structural/real-provider acceptance, not semantic proof of ChatGPT superiority, expected-return ranking or complete AC acceptance.

Ubuntu checkout is now ad0f738. Active systemd process remains the previous code: sudo restart was BLOCKED because interactive authentication is required. PETR4 active HTTP still PASS: 85 bars through 2026-10-02, b3_cotahist/oplab, zero options, 0.15s. Do not conflate candidate ASGI with active HTTP. Next manual action: restart b3-runtime.service; then verify active /version contains opportunity_screen_policy B3_OBSERVED_STOCK_SCREEN_V1 and validate the new deterministic screen through HTTP. No repeat of all senior requests needed.

Details: docs/OPPORTUNITIES_OBSERVED_SCREEN_2026-10-03.md. Economic valuation/expected-return ranking, complete financed switching, stronger model routing and desktop visual acceptance remain open. No new ledger; V4.3/UNKNOWN/PIT preserved.


## 2026-10-03 — active HTTP acceptance after user restart

User reported restart. Read-only Ubuntu workflow run 37128404693 SUCCESS verifies the actual systemd HTTP service, not candidate ASGI. `/version` exposes B3_OBSERVED_STOCK_SCREEN_V1. Both Opportunities observed objectives PASS: four selected assets, three comparable ranked assets, zero LLM calls, expected return null. Risk 4.32s, liquidity 2.96s; PARTIAL_COMPARABLE_UNIVERSE retained. PETR4 active HTTP PASS: 85 bars through 2026-10-02, b3_cotahist/oplab, zero options. No runtime mutation or repeated senior synthesis.

This supersedes the pending service restart above. No further restart needed for this documentation-only checkpoint. Browser visual acceptance and semantic superiority remain unproven. Next implementation priorities: reduce senior context/latency without weakening evidence, improve objective/constraint-aware economic comparison using existing authoritative data, and complete funded switching gaps. Missing valuation/targets/expected return must remain UNKNOWN, rather than replacing them with historical volatility/liquidity.


## 2026-10-03 — exact repeated senior context projection

Code d0fd7114a626b17c2277af1c9339add7a878bb73. Senior prompt now represents exactly repeated structured blocks of at least 512 characters as backward JSON Pointer references, retaining one complete copy. JSON normalization matches the previous boundary; unique values, sources, timestamps, null/UNKNOWN and distinct provenance remain. Reserved reference-key collisions disable projection. API facts and ranking are unchanged. CI run 37130656329 SUCCESS; three additional lossless/identity/collision regressions.

Real Ubuntu candidate run 37130654326 SUCCESS: both deterministic stock objectives and four-asset senior comparison PASS. Senior HTTP 200, no error, four assessments with implications/unknowns, six sources, 71.96s total. Final reason stage 41.68s, 103411 input characters, cache MISS. Previous focused run 81.15s: single-run difference is not a controlled proof of stable latency improvement or semantic parity/superiority. Candidate checks structural coverage only; full response remains private. No advanced model routing or economic ranking is added.

Runtime checkout updated to d0fd711; systemd restart BLOCKED by interactive sudo. Active prior HTTP remains healthy. Next: when loading this block, restart service; then validate active senior response. Broader economic comparison, financed switching, model routing and visual acceptance remain open. Preparation/additional context still accounts for roughly 30s, requiring a separate measured correction without removing unique evidence or synchronously blocking on DeepSeek.


## 2026-10-03 — financed stock-switch increment and economic comparison priorities

Previous context-projection update accepted after user restart: active HTTP workflow 37131192345 SUCCESS; four assets, HTTP 200, four structured assessments, 72.96s. No pending restart for that prior block.

New code e4a876835a2313f5c1ba47e89d395a7144f0ce14 adds an explicit Strategy Lab funded-switch form and canonical HOLD-vs-linked-SWITCH comparison. Integer sale quantity must fit the admissible current long stock position. Existing strict stock-screen evidence supplies both indicative quotes and portfolio facts. Decimal cashflow computes gross sale, explicit fees/taxes, net proceeds, integer target shares and residual cash. Missing costs prevent net sizing; zero is used only if explicitly supplied. Related option obligations remain restrictions, never released or netted by selling shares. Current-only; no valuation, expected return, tax estimation or order execution. This closes decision-time financing plumbing, not full portfolio collateral/scenario/economic acceptance.

CI run 37131884672 SUCCESS: 840 Python tests, React build and rendering regression. Real candidate Ubuntu run 37131880994 SUCCESS: actual portfolio/quote cash conservation, zero LLM deterministic calculation, explicit hypothetical zero-fee/tax test inputs. Focused real senior: HTTP 200, two assessments matching exact canonical alternative IDs, implications/unknowns present, 35 sources, 85.08s total; final reason 42.91s, 113228 characters, cache MISS. Structural acceptance does not prove qualitative superiority to ChatGPT. Real responses remain private. Prior failed gates caught frontend typing and missing telemetry after immutable response construction; both fixed before runtime update.

Ubuntu checkout now e4a8768; new funded-switch service restart BLOCKED by interactive sudo. Active process still prior projection code. Next manual restart then active funded-switch HTTP acceptance; do not repeat all earlier senior comparisons. Desktop form visual acceptance remains pending.

User-defined priorities now explicitly include: (1) compare two PUT sales with potentially different expiries using risk of exercise, premium/risk and duration, beyond the current same-underlying/same-expiry chain restriction; (2) compare stock BUY A vs BUY B by appreciation potential and future dividends, distinguishing announced vs estimated distributions, institution targets/valuation, downside and portfolio impact. Calibrated return/exercise probabilities require explicit valid model/horizon; absent evidence remains UNKNOWN. Neither case is implemented by observed-volatility/liquidity ordering. Next implementation: different-expiry PUT comparison, then evidence-backed stock economic comparison. Full requirement details in docs/FUNDED_SWITCH_AND_PUT_COMPARISON_2026-10-03.md. No new ledger, V4.3 authority and PIT preserved.


## 2026-10-03 — different-expiry two-PUT comparison candidate acceptance

Funded-switch active HTTP accepted after user restart: read-only run 37132741398 SUCCESS, actual systemd service, 2.10s, cash conservation and zero LLM calls. Supersedes the prior funded-switch restart pending status.

Two-PUT code c568097383c8151cdcd8775b8bd23b9cca731f1f. Uses existing two-alternative StrategyComparison, strict AssetEvidencePack acquisition and existing ITM/touch proxy. Generic Strategy Lab form accepts Vender PUT on both sides, exact current OPLAB contract IDs, distinct expiry/underlying; displays actual multiplier, premium/capital, break-even, maximum loss, duration, liquidity fields and separate model risks. Conditional objectives: lower model expiry ITM, or higher gross premium/capital normalized to 30 days. Default no winner. Different expiry risks cover different periods, normalized gross premium is not expected return, unknown costs/early assignment/personal frequency are not inferred. Current chain completes before a common PIT cutoff; identities/duplicates/future availability/stale option quotes rejected. Unknown/stale underlying spot prevents risk ranking. HTTP and service refuse historical pair replay without proven historical contract metadata availability. Common incomplete terminal scenarios cannot choose a maximin winner. No new ledger or execution.

CI run 37133442742 SUCCESS: 847 Python tests, React build and rendering regression. Real candidate Ubuntu run 37133438675 SUCCESS: actual PETR4 two-expiry PUT contracts, positive two-sided bid indications. Gross-premium objective 0.75s, conditional order; risk objective 0.55s, UNKNOWN_OBJECTIVE_INPUTS for the selected actual records. Do not claim live calibrated risk ranking from that test; helper reason exists in the private response, exact missing model dependency still requires focused data review. Actual senior HTTP 200, no error, two assessments matching canonical alternatives with implications/unknowns, 76.29s. Initial code run also passed (37133246199, 84.72s senior), no controlled stable speed gain asserted. Structural acceptance is not proof of semantic superiority, execution or broad AC completion. Full responses remain private.

Runtime checkout updated to c568097; restart BLOCKED by interactive sudo. Active service remains the funded-switch block until user restarts. Next: restart once, validate new pair through active HTTP and inspect risk-input availability without inventing IV or probabilities. Browser visual acceptance and cross-underlying real acceptance remain pending; live test covered one underlying with different expiries. Same-chain multi-contract comparison remains limited to one expiry by design. Next economic implementation: BUY A vs BUY B using sourced targets/valuation and announced versus estimated future dividends; positive-return probability requires an explicit validated horizon/model or remains UNKNOWN. See docs/TWO_PUT_DIFFERENT_EXPIRIES_2026-10-03.md.


## Final two-PUT candidate and observed risk evidence — 2026-10-03

Validated code 5c616e4955956e280d73c1f15545360696153aa2. GitHub CI 37134301848 SUCCESS; real Ubuntu candidate 37134298644 SUCCESS. Actual PETR4 contracts with different expiries: deterministic gross-premium objective 823.0ms, CONDITIONAL_OBJECTIVE_ONLY; model-risk objective 792.6ms, UNKNOWN_OBJECTIVE_INPUTS; zero LLM calls. Both contracts have observed strike and breakeven cushions, now rendered from backend fractions. Senior HTTP 200, no error, two canonical assessments, 87.40s. Structural acceptance does not establish calibrated probabilities, semantic superiority or browser acceptance.

Focused read-only diagnostic run 37134104828 establishes the cause of missing model probability: selected contracts have underlying quotes, but no admissible implied volatility. The configured OPLAB current chain response exposes volume-related fields but no IV/Greeks fields in any returned row. This is a gap in that endpoint response, not evidence that all provider endpoints or subscriptions lack these data. Existing adapter recognizes implied_volatility/iv. Do not fabricate IV, substitute realized volatility silently, or convert missing risk into zero. Observed cushion is descriptive distance, not an exercise probability.

Ubuntu checkout is 5c616e4. Service restart was BLOCKED by interactive sudo; candidate validation must not be described as deployment of the new pair code. Funded-switch active HTTP already passed 37132741398. Next runtime action: user executes sudo systemctl restart b3-runtime.service once, then validate pair through active HTTP. Browser visual acceptance and real cross-underlying acceptance remain pending. Next economic block: BUY A versus BUY B with sourced valuation/targets, announced versus estimated future dividends, and explicit horizon/model requirements for probability of positive return. Preserve UNKNOWN, deterministic authority, PIT and V4.3; no ledgers.
