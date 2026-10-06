# Retomada — Inteligência do frontend B3 (2026-10-05)

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

## Contexto e estado confirmado

- Branch: `feature/react-functional-v43-integration`.
- Commit consultado no GitHub: `e39c2202152aacc17581a1cf9a4350f2ef540e32` (`ui: retain fundamental source provenance`).
- A checagem de CI registrada para esse commit passou em backend tests, build React e validação de renderização. Isso valida o código daquele commit, mas não confirma que o backend Ubuntu ou a cópia local do Windows estejam rodando essa mesma versão.
- O usuário encerrou o trabalho em 04/10/2026 e pediu retomar amanhã para aportar inteligência em **Opportunities**, **Strategy Lab** e **Market Intelligence**.

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

> Continue no repositório `edmilsonandradefonseca/b3-investment-options-agent`, branch `feature/react-functional-v43-integration`. Leia este checkpoint atualizado e os documentos autoritativos da arquitetura V4.3, dos casos de uso/rastreabilidade e do plano de cobertura React UC-01…UC-12. Confirme branch, HEAD, PR #66 e CI antes de alterar código. **Antes das telas, corrija o schedule noturno:** o run de 22h falhou em `DividendRefreshJob.run → _validated_equity_ticker` ao validar a lista monitorada. Reproduza sem expor carteira, identifique a identidade inválida, preserve a posição original, trate o caso explicitamente e faça o refresh de dividendos/alvos continuar para os tickers válidos. Adicione regressão, rode no host ativo e confirme manifesto/resultado SUCCESS. Unifique os instaladores que sobrescrevem `b3-local-evidence-analyst.timer`. O diagnóstico completo está neste checkpoint. **Opportunities já passou a aceitação funcional integrada no Ubuntu e no navegador real; não a reabra sem regressão ou critério existente comprovadamente pendente.**
>
> Prioridade 1: concluir **Strategy Lab (UC-04)**. Reproduza ITUB4 × BBDC4 com orçamento de R$ 10.000 e sem premissa de futuro inventada. Confira o payload real e corrija causas comprovadas para: janelas comuns de retorno/histórico, métricas bancárias comparáveis e unidades, corte temporal de São Paulo/PIT, cálculo explicado de quantidade/capital, apresentação de cenários hipotéticos editáveis e síntese que explique o que favorece cada alternativa e o que impede preferência. Preserve fatos, hipóteses e UNKNOWN separados; não duplique cálculos financeiros no React.
>
> Prioridade 2: concluir **Market Intelligence (UC-05/06/10)** com PETR4 e a posição/opção efetivamente aberta. Integre histórico, retornos e indicadores técnicos, regime/fatores, notícias/eventos com fonte e datas, fundamentos qualificados e exposição da carteira. Explique sinais concordantes/divergentes e condições que invalidariam a leitura; diferencie ausência de evidência de busca não executada e dado fora do corte. Não invente valuation, notícia, preço-alvo, probabilidade ou recomendação de ordem.
>
> Em cada área: reproduza o defeito com request/response sanitizados, rastreie frontend → API → serviço/dado, faça a menor correção que resolve a causa, rode regressões focadas/CI, valide o serviço Ubuntu ativo depois do reinício autorizado e faça walkthrough visual com capturas. Atualize este checkpoint com commits, critérios UC/AC cobertos, evidência, limitações e próximo passo. Preserve V4.3, proveniência/PIT, UNKNOWN e controle humano.

## Sequência recomendada

0. **Schedule, correção operacional:** corrigir a falha do refresh noturno por ticker inválido e unificar a definição do timer do analista; confirmar as execuções e manifests no Ubuntu.
1. **Strategy Lab (UC-04):** reproduzir ITUB4 × BBDC4; confrontar payload e UI com os defeitos registrados; corrigir dados/unidades/corte antes da síntese; validar cenários e resultado real.
2. **Market Intelligence (UC-05/06/10):** reproduzir PETR4 com carteira/opção; validar fontes e timestamps; integrar interpretação técnica, regime/eventos e exposição existente.
3. Rodar CI e aceitação no Ubuntu com o serviço atualizado; completar walkthrough visual e guardar evidência sem payload financeiro bruto.
4. Atualizar este checkpoint e a rastreabilidade AC-01–28/UC correspondente. Só então considerar essas áreas fechadas. A PR #66 permanece draft até decisão de integração.
