# Retomada — Inteligência do frontend B3 (2026-10-05)

## Plano de fechamento do Lab e primeiro incremento — 06/10/2026 BRT

Plano de execução: [STRATEGY_LAB_CLOSURE_2026-10-06.md](STRATEGY_LAB_CLOSURE_2026-10-06.md), subordinado à V1.2, LAB-01–07 e AC existentes. Cinco entregas: (1) intenção/posição e esclarecimento; (2) alternativas/pernas/quantidades; (3) manter/encerrar/rolar com fluxos e cenários; (4) carteira completa antes/depois e tela central; (5) aceite real integrado.

Primeiro incremento publicado em `8fd802d473fc4c4aa1dbcc1656c54075e8c7175b`: pedido genérico de operação sem código exato recebe `NEEDS_CLARIFICATION` no centro, sem cadeia nem chamada sênior. A sessão conserva o esclarecimento para a continuação e mostra “Aguardando identificação do contrato”, em vez de síntese concluída. Perguntas conceituais/teses e comparações estruturadas seguem seus fluxos. Não representa seleção/validação de contrato nem cálculo de rolagem; LAB-01 integral permanece em andamento.

[CI 37466654990 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37466654990): testes e build aprovados, incluindo teste HTTP que bloqueia qualquer dispatch externo antes do esclarecimento. Walkthrough da nova revisão ainda deve concluir; não confundir o incremento com o bloco anterior já ativo/aceito. Não pedir novo reinício até concluir a revisão de código que será ativada.

Próximo incremento concreto: ligar contrato selecionado à posição do snapshot vigente; validar unidade/multiplicador e quantidade, permitir alternativas de manter/encerrar/rolar sem a restrição de duas alternativas, preservando compatibilidade da compra entre ações.


## Aceite do bloco no processo ativo — 06/10/2026, 09h22 BRT

- Usuário reiniciou o serviço. Gate [37462396255 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37462396255) confirmou PID 446803, início em 06/10 às 09h17m31 BRT, processo posterior à instalação e hashes de seis módulos do backend iguais à revisão testada. Não houve novo reinício pelo workflow.
- **Aceito neste bloco:** entrada natural “Tenho R$ 10 mil. Comprar ITUB4 ou BBDC4?”, duas alternativas, 274 sessões comuns, histórico recente, conservação de orçamento bruto e síntese sênior na API HTTP ativa. Etapa determinística 1,3 s; sênior 97,59 s.
- **Aceito neste bloco:** síntese sênior Market Intelligence PETR4 com tese/racional e contratos de alvos/proventos armazenados na API HTTP ativa, 67,55 s. Cobertura observada: `UNKNOWN_NO_ADMISSIBLE_TARGETS` e `PROVIDER_UNAVAILABLE`. O sucesso de integração NÃO certifica cobertura completa nem recupera o provedor; estes estados continuam explícitos.
- Visual real [37446374999 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37446374999); candidato final [37446102693 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37446102693), 52 regressões focadas e as duas sínteses. [CI 37462406473 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37462406473).
- O bloqueio de ativação descrito abaixo está superado para este bloco. As tentativas antigas com sudo continuam como histórico, não como bloqueio atual.
- **Strategy Lab e Market Intelligence permanecem parciais no escopo integral V1.2:** não marcar UC-04/05/06/10 completos só por este par de ações e PETR4. Próximos aceites: variantes PUT/CALL/rolagem e hipóteses do Lab; regime/fatores tipados e cobertura de fontes em MI. Opportunities permanece aceita.


## Implementação Strategy Lab e Market Intelligence — 06/10/2026 UTC

Revisões publicadas no PR #66: `2e50a735c5ca49d82c26e020d15248ecaab450a4`, `569a3d0e7e1214c34d477ec29fc70e9b2aeb203d`, `8ff9ccdec5c6cac32d539e897ac022dc088d7b1f` e `ead13f5f41f67b9e6271982799a931d752328377`. O escopo implementado abaixo **não constitui aceite completo** de UC-04/05/06/10.

- Strategy Lab: corrigido o corte interativo congelado antes da aquisição, que excluía observações recém-obtidas dos retornos. Cortes históricos explícitos continuam fixos. Backend agora fornece série base 100 somente nas sessões comuns e base uniforme; gráfico React apenas exibe o cálculo. Compra bruta antes de custos explicita quantidade inteira, valor aplicado e residual com conservação do orçamento; quantidade líquida, capacidade de financiamento e renda pessoal continuam UNKNOWN sem os respectivos insumos. Fundamentos sem par ficam em detalhe, não na tabela principal. Continuação exclui respostas associadas a outra revisão da carteira.
- Market Intelligence: síntese sênior aparece primeiro no contexto amplo; atualização preserva resultado e fundamentos anteriores em caso de falha. Evidência armazenada de alvos institucionais primários e proventos admissíveis integra o contexto e tem apresentação própria com fontes/datas. Não são criados consenso, valuation ou pagamento pessoal. Gráfico e indicadores usam preços ajustados somente com cobertura integral válida; caso contrário, série bruta uniforme. Notional negociado usa fechamento efetivo.
- Validação de código: [CI 37446107085 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37446107085), **967 testes passaram**, build React e verificador da apresentação passaram. Localmente passaram 18 testes de indicadores e 17 testes de compra/economia. Os testes focados de StrategyEvidenceService já passaram no runner Ubuntu no primeiro bloco.
- Dado real candidato: [37445107735](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37445107735) confirmou entrada natural ITUB4 × BBDC4, R$ 10 mil, 274 sessões comuns, histórico recente e conservação do orçamento bruto. A chamada sênior seguinte falhou na verificação HTTP; o log inicial não registrou o status, então a causa ainda NÃO foi atribuída. Diagnóstico foi ampliado e o histórico no contexto foi reduzido aos campos necessários, sem retirar ativos ou sessões. Repetições [37445676627](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37445676627) e [37446102693](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37446102693) aguardavam o runner neste checkpoint; exigem narrativa sênior e o caso MI PETR4.
- Visual real [37445107890](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37445107890) avançou pela comparação, cenários, ativo PETR4 e Opportunities, mas falhou na nova asserção do contexto amplo: o teste procurava `telemetry.llm_calls`, que não faz parte da resposta sênior. A síntese retornara COMPLETED. A asserção foi corrigida para exigir ausência de erro, tese/racional e `telemetry.stages.reason`. Nova execução [37446374999](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37446374999) pendente; NÃO declarar walkthrough aprovado antes do PASS.
- Ativação: [37445107702](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37445107702) instalou o primeiro bloco no checkout Ubuntu e passou 21 testes focados, mas `sudo systemctl restart b3-runtime.service` foi bloqueado por autenticação interativa (`RUNTIME_RESTART=BLOCKED_AUTHENTICATION_REQUIRED`). O processo ativo não foi atualizado pelo workflow. Checkouts candidatos do Actions não equivalem ao processo systemd.

Próximo passo: ler os testes candidatos e resolver a falha HTTP sênior com a evidência nova; confirmar o checkout de produção na revisão final, obter reinício autenticado e então passar o gate HTTP ativo e o walkthrough. Continuam abertos os aceites integrais das variantes PUT/CALL/rolagem e das hipóteses do Lab, além de regime/fatores tipados e cobertura de fontes em MI conforme a especificação V1.2. Opportunities permanece aceita salvo regressão comprovada. A cadeia manual de coleta/Qwen permanece com os limites documentados abaixo.


## Verificação real do Qwen — 06/10/2026, 06h32 (America/Sao_Paulo)

- Diagnóstico read-only no Ubuntu: [run 37443614434 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37443614434). O sucesso deste workflow certifica a leitura, não o sucesso completo da cadeia.
- Store de produção `/opt/b3-runtime/data`: um dossier READY nas últimas 24 horas, modelo `qwen3:4b-instruct-2507-q4_K_M`, criado em 05/10 às 22h10m20 BRT. Nenhum dossier FAILED/DEGRADED observado nessa janela. Fila atual vazia. Último manifesto do consumidor em 06/10 às 06h25 registra zero itens processados e zero falhas; foi uma execução sem trabalho.
- Store usada pela repetição manual da coleta `/opt/b3-investment-options-agent/data`: quatro itens PENDING, todos vencidos para processamento, sem dossier nem manifesto do Qwen. Não confundir esta fila com a fila vazia da produção. A configuração efetiva do teste manual e a do consumidor devem ser alinhadas antes do aceite integrado; não mover nem duplicar filas sem verificar identidade/fingerprint e origem.
- A repetição da coleta [run 37443192215](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37443192215) gravou resumo novo, mas terminou PARTIAL/exit 2: 24 tickers aceitos, quatro identidades rejeitadas, cobertura CVM de 22/24, duas identidades de emissor sem resolução; zero falhas por ativo e 24 projeções de dividendos. O KeyError não voltou. O critério de aceite não foi relaxado.
- Conclusão: Qwen processou com sucesso a evidência enfileirada na produção em 05/10, mas a cadeia completa da repetição manual NÃO está validada. Próximo passo operacional: usar no workflow a mesma configuração/data_dir efetiva do serviço systemd, confirmar os quatro itens sem duplicação e resolver/explicitar a cobertura dos dois emissores CVM.
- Opportunities continua aceita conforme o checkpoint de encerramento; não reabrir com base em estados históricos da descrição da PR. Strategy Lab e Market Intelligence continuam pendentes de fechamento.

## Atualização operacional — 06/10/2026 UTC

- A correção da coleta noturna está em `scripts/run_nightly_intelligence.py`: identidades monitoradas são validadas e deduplicadas antes das etapas agendadas; ativos inválidos ficam fora dos provedores de ações/dividendos, sem alterar a carteira. O resumo `runner_latest.json` registra contagem e hashes curtos, sem símbolos rejeitados.
- O teste integrado no Ubuntu alcançou as etapas de resumo após a coleta, mas terminou com `KeyError` em `_safe_target_refresh_summary`; isso foi corrigido para ler apenas campos presentes. Regressão incluída.
- CI passou para o commit atual [run 37403222308 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37403222308). O job Ubuntu [run 37403217336](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37403217336) está aguardando o runner para repetir a coleta com o caminho resolvido por `settings.data_dir`.
- O checkout Ubuntu já havia sido atualizado e os 11 testes focados passaram nele; a revisão agora adiciona o caso de regressão do resumo. A coleta live só fecha quando o workflow atual terminar com sucesso e um manifesto novo for confirmado.
- Os timers CVM/reconciliação estavam ativos na última verificação (05/10). A discrepância entre instaladores do timer do analista continua por consolidar. PR #66 continua aberta em draft.

## Próximas áreas

Strategy Lab (UC-04) e Market Intelligence (UC-05/06/10) continuam na ordem aprovada. Fechar primeiro a validação live da coleta e unificar o calendário do timer do analista. Não reabrir Opportunities sem regressão ou critério aprovado comprovadamente pendente.

## Checkpoint de encerramento — 05/10/2026 (America/Sao_Paulo)

### Estado confirmado

- Branch: `feature/react-functional-v43-integration`; PR [#66](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/pull/66) continua aberta em draft.
- Revisão de código/teste visual: `a57745a1113c098492a752c3673814232b1bf052`. O commit atual ajusta o validador visual; não altera o backend de produção.
- **Opportunities — vertical funcional aceita**: reinício de `b3-runtime.service` feito pelo usuário; o gate confirmou processo ativo posterior à instalação do backend e ausência de diferenças nos módulos de Opportunities entre o runtime e o código testado.
- Aceitação integrada pelo HTTP ativo: [run 37395826026 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37395826026). HTTP 200, síntese sênior COMPLETED, 21 ações da carteira, 11 subjacentes de opções, universo completo de 24 ativos, 8 ativos no contexto de pesquisa e 57 fontes; resposta em 76,6 s. Sem truncar o universo.
- Aceitação visual real: [run 37396778650 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37396778650). CI e build passaram; walkthrough em 1920, 1440 e 1366 px; oito áreas navegadas; busca automática e manual em Opportunities responderam HTTP 200; tratamento de indisponibilidade e nova tentativa passaram; zero erros de página/JavaScript.
- [Capturas visuais](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37396778650/artifacts/11383635486) retidas como artefato até 09/10/2026. Nenhum payload bruto foi anexado.
- O workflow amplo de fechamento falhou antes do gate HTTP porque o runner tentou reiniciar o serviço sem sudo interativo. Isso não bloqueou a aceitação específica: o usuário reiniciou o serviço e os gates ativo e visual passaram depois.
- Esta aceitação fecha o fluxo funcional acordado de Opportunities (descoberta a partir de candidatas + snapshot integral, síntese, detalhe, atualização manual/automática e estados de erro). O ranking observado continua sujeito aos limites documentados na política: não é retorno esperado nem recomendação automática de ordem.

### Próximas áreas

Sim: os próximos fechamentos são **Strategy Lab (UC-04)** e **Market Intelligence (UC-05/06/10)**, nesta ordem. Reusar os critérios existentes AC-01–28 e a rastreabilidade por UC; não criar especificação concorrente. Não reabrir Opportunities sem regressão ou requisito já definido que ainda falhe.

### Verificação real do schedule — 05/10/2026, 22h24 (America/Sao_Paulo)

Diagnóstico read-only no runner Ubuntu: [workflow 37398980858](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37398980858); CI do diagnóstico [37398984690 — SUCCESS](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37398984690).

| Unidade | Estado observado | Último resultado |
|---|---|---|
| `b3-continuous-intelligence.timer` | enabled/active; agenda em dias úteis, 15 min, janela 08h–18h45 BRT | Execução de 22h15 terminou com sucesso, mas fora da janela foi SKIP; último manifesto de coleta PASS às 18h45; 1.930 arquivos de evidência CVM persistidos |
| `b3-cvm-reconciliation.timer` | enabled/active; 20h30 em dias úteis | serviço SUCCESS; manifesto PASS e 19 arquivos de evidência reconciliada |
| `b3-local-evidence-analyst.timer` | enabled/active; timer instalado executa a cada 15 min | 22h10 SUCCESS; próxima execução prevista às 22h25 |
| `b3-local-relevance-screen.timer` | enabled/active | serviço estava executando às 22h20 |
| `b3-nightly-intelligence.timer` | enabled/active; 22h em dias úteis | serviço **FAILED** às 22h00 por `ValueError` em `DividendRefreshJob.run → _validated_equity_ticker`; manifesto registrou 30 ativos, 29 sem cobertura suficiente, 1 análise enfileirada e zero falhas por ativo antes do erro posterior |

A falha noturna ocorre quando um ticker monitorado inválido entra na validação em lote de dividendos; a exceção interrompe a etapa de refresh de dividendos/alvos. O runtime contém 30 identidades monitoradas, mas o nome da identidade inválida não foi exposto no diagnóstico. Corrigir preservando a carteira original e registrando explicitamente a identidade rejeitada; não filtrar silenciosamente nem transformar a posição em ticker negociável.

Os instaladores noturno e contínuo definem calendários diferentes para `b3-local-evidence-analyst.timer`. O systemd ativo agora mostra o calendário periódico (próxima execução 22h25), então a configuração noturna das 22h15 não é a que está instalada neste host. Consolidar a definição para evitar que um instalador sobrescreva o outro.

Conclusão operacional: schedule **parcialmente operacional**. Com Ubuntu ligado, timers ativos disparam; a coleta CVM e reconciliação gravam evidência, mas o job noturno não terminou com sucesso nesta execução. Esses fluxos atualizam stores de evidência/artefatos e filas derivados; não importam automaticamente novos extratos BTG/notas nem substituem o carregamento da carteira/ledger.

## Contexto de referência — observações de 04/10

Este bloco preserva o diagnóstico visual e técnico feito em 04/10, antes do aceite funcional de Opportunities em 05/10. Os estados atuais, o schedule e as próximas ações estão no checkpoint de encerramento no início deste documento. O commit `e39c2202152aacc17581a1cf9a4350f2ef540e32` e a ressalva abaixo são contexto histórico, não a revisão atual do branch/runtime.

As evidências a seguir continuam sendo a linha de base para Strategy Lab (ITUB4 × BBDC4) e Market Intelligence (PETR4). Opportunities foi aceita no fluxo funcional integrado e visual descrito no checkpoint atual.

## Evidências do teste Strategy Lab ITUB4 × BBDC4

Saída exibida pelo usuário em 04/10, 22:02 (São Paulo):

1. A comparação informa retornos de 1 semana a 1 ano como indisponíveis, embora haja histórico de mercado e métricas de risco por ativo.
2. Dos fundamentos apresentados, zero de 18 métricas são comparáveis; o conjunto ITUB4 possui muitos campos BRAPI e BBDC4 apenas alguns (LPA, P/L e valor de mercado). A tela despeja métricas sem par e repete “não comparável”.
3. Unidades parecem semanticamente incorretas: `debtToEquity` apareceu como reais; `revenueGrowth` e `revenueGrowthAnnual` também apareceram como reais. Confirmar no payload e no classificador antes de corrigir.
4. As cotações/indicadores têm datas após o corte local mostrado (há campos datados de 05/10 quando o corte exibido é 04/10, São Paulo). Auditar timestamp UTC → data de São Paulo e elegibilidade point-in-time na cadeia inteira.
5. A seção econômica mostra quantidade, custo de compra e caixa residual como UNKNOWN sem explicar bem o que poderia ser calculado com preço corrente e orçamento de R$ 10.000 antes de taxas.
6. A tabela de cenários fica vazia e a explicação de ausência de premissas é insuficiente para ajudar a decidir.
7. A conclusão “comparação sem preferência” não resume claramente o que favorece cada banco, o que é comparável e o que impede decisão.

Não presumir a causa: verificar se a tela consultada usa o commit novo e se o serviço Ubuntu foi atualizado. Um payload antigo pode explicar diferenças entre o que o backend atual deveria fornecer e o que o usuário viu.

## Evidências do teste Market Intelligence PETR4

Na análise reportada em 04/10, a decisão ficou essencialmente em “aguardar” por ausência de caixa, cobertura total da carteira, cadeia executável, valuation e pesquisa específica. A tela listou sinais técnicos/fundamentais, mas não os transformou numa conclusão acionável. A área de notícias mostrou evidência PETR4 zero e busca complementar pendente; trechos de fundamentos citavam métricas genéricas sem interpretação suficiente. A carteira indicava 4.450 ações e CALL vendida PETRK376, enquanto a reconciliação da posição aparecia como lacuna.

O sistema precisa explicar o que os dados atuais significam para o ativo e para a posição existente, separar fatos, interpretação, hipóteses e desconhecidos, e propor alternativas condicionais quando os dados permitirem. Não inventar notícia, valuation, cadeia de opções, caixa, custos, probabilidade ou preço-alvo.

## Objetivo da próxima sessão

A próxima sessão começa corrigindo e revalidando o job noturno, que falhou no refresh por uma identidade inválida na lista monitorada. Depois conclui Strategy Lab e Market Intelligence pelo fluxo ponta a ponta, com casos reais, critérios rastreáveis, evidência da API ativa no Ubuntu e walkthrough visual. As observações de 04/10 registradas acima são a linha de base para comparação. Opportunities fica encerrada no escopo funcional validado; só reabrir se surgir regressão ou uma lacuna objetiva contra os critérios já aprovados.

## Prompt para a próxima sessão

> Continue no repositório `edmilsonandradefonseca/b3-investment-options-agent`, branch `feature/react-functional-v43-integration`. Leia este checkpoint atualizado e os documentos autoritativos da arquitetura V4.3, dos casos de uso/rastreabilidade e do plano de cobertura React UC-01…UC-12. Confirme branch, HEAD, PR #66 e CI antes de alterar código. A correção para a falha `DividendRefreshJob.run → _validated_equity_ticker` já está no código: a lista é filtrada de forma explícita antes dos provedores, a carteira não muda, identidades rejeitadas são resumidas por hash e 11 regressões passaram no Ubuntu. Primeiro verifique o workflow [37403217336](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37403217336) e obtenha o manifesto live novo; ele está aguardando o runner. A execução anterior alcançou o resumo final e falhou com `KeyError`, corrigido em commit posterior. Não declare a coleta live validada sem o resultado deste workflow. Depois consolide o calendário duplicado de `b3-local-evidence-analyst.timer` nos instaladores. O diagnóstico e limites estão neste checkpoint. **Opportunities já passou a aceitação funcional integrada no Ubuntu e no navegador real; não a reabra sem regressão ou critério existente comprovadamente pendente.**
>
> Prioridade 1: concluir **Strategy Lab (UC-04)**. Reproduza ITUB4 × BBDC4 com orçamento de R$ 10.000 e sem premissa de futuro inventada. Confira o payload real e corrija causas comprovadas para: janelas comuns de retorno/histórico, métricas bancárias comparáveis e unidades, corte temporal de São Paulo/PIT, cálculo explicado de quantidade/capital, apresentação de cenários hipotéticos editáveis e síntese que explique o que favorece cada alternativa e o que impede preferência. Preserve fatos, hipóteses e UNKNOWN separados; não duplique cálculos financeiros no React.
>
> Prioridade 2: concluir **Market Intelligence (UC-05/06/10)** com PETR4 e a posição/opção efetivamente aberta. Integre histórico, retornos e indicadores técnicos, regime/fatores, notícias/eventos com fonte e datas, fundamentos qualificados e exposição da carteira. Explique sinais concordantes/divergentes e condições que invalidariam a leitura; diferencie ausência de evidência de busca não executada e dado fora do corte. Não invente valuation, notícia, preço-alvo, probabilidade ou recomendação de ordem.
>
> Em cada área: reproduza o defeito com request/response sanitizados, rastreie frontend → API → serviço/dado, faça a menor correção que resolve a causa, rode regressões focadas/CI, valide o serviço Ubuntu ativo depois do reinício autorizado e faça walkthrough visual com capturas. Atualize este checkpoint com commits, critérios UC/AC cobertos, evidência, limitações e próximo passo. Preserve V4.3, proveniência/PIT, UNKNOWN e controle humano.

## Sequência recomendada

0. **Schedule, aceite operacional:** confirmar a execução live da coleta pelo workflow pendente e o resumo `runner_latest.json`; depois unificar a definição duplicada do timer do analista e comprovar o calendário instalado.
1. **Strategy Lab (UC-04):** reproduzir ITUB4 × BBDC4; confrontar payload e UI com os defeitos registrados; corrigir dados/unidades/corte antes da síntese; validar cenários e resultado real.
2. **Market Intelligence (UC-05/06/10):** reproduzir PETR4 com carteira/opção; validar fontes e timestamps; integrar interpretação técnica, regime/eventos e exposição existente.
3. Rodar CI e aceitação no Ubuntu com o serviço atualizado; completar walkthrough visual e guardar evidência sem payload financeiro bruto.
4. Atualizar este checkpoint e a rastreabilidade AC-01–28/UC correspondente. Só então considerar essas áreas fechadas. A PR #66 permanece draft até decisão de integração.
