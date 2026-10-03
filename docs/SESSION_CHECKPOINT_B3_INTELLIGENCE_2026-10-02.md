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
