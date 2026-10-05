# Retomada — Inteligência do frontend B3 (2026-10-05)

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

## Objetivo de amanhã

Fazer uma revisão profunda, guiada por casos reais, das três telas. O resultado deve ser um fluxo útil de apoio à decisão, ancorado em dados determinísticos e histórico armazenado, com síntese interpretativa clara e limites explícitos. A tarefa não termina com uma revisão textual: reproduzir, corrigir, testar e deixar uma versão verificável pronta para o usuário.

## Prompt para iniciar amanhã

> Continue o desenvolvimento no repositório `edmilsonandradefonseca/b3-investment-options-agent`, branch `feature/react-functional-v43-integration`. Leia este checkpoint e a especificação `docs/REACT_FRONTEND_UC01_UC12_COVERAGE_PLAN_2026-09-27.md`. Não trate “build passou” como prova de que os serviços ativos estão atualizados. Meu objetivo é elevar substancialmente a inteligência útil das telas **Opportunities (UC-03)**, **Strategy Lab (UC-04)** e **Market Intelligence (UC-05/06/10)**.
>
> **Primeiro, reconstrua o caminho real dos dados e reproduza as falhas antes de editar.**
>
> 1. Confirme branch/HEAD e alterações locais. Identifique quais versões estão rodando no frontend Windows e no backend Ubuntu, consultando o endpoint de health/build ou outro identificador existente. Não sobrescreva trabalho local. Confirme o contrato real dos endpoints e compare o JSON recebido pela tela com o que o backend atual produz.
> 2. Reproduza pelo menos estes casos, com request/response guardados de forma sanitizada:
>    - Market Intelligence: PETR4, incluindo carteira, ações/opções abertas, indicadores, notícias/eventos e histórico armazenado.
>    - Strategy Lab: comprar ITUB4 versus comprar BBDC4, orçamento de R$ 10.000, sem hipótese futura informada.
>    - Opportunities: ranking de candidatas e operações compatíveis com o perfil real do usuário — compra/venda de ações, venda de PUT, CALL coberta, fechamento com lucro e rolagem — sempre respeitando caixa, posições e opções da carteira.
> 3. Use corte temporal de São Paulo. Para cada informação, preserve data de observação, disponibilidade, publicação e fonte. Uma notícia futura ou dado posterior ao corte não pode influenciar a síntese. Investigue especificamente o caso de timestamps UTC de 05/10 aparecendo num relatório de 04/10 à noite em São Paulo.
> 4. Rastreie no código e nos dados por que retornos históricos foram “Indisponível”, por que os fundamentos dos dois bancos tiveram cobertura muito desigual e por que unidades como `debtToEquity`/crescimento podem ser renderizadas como moeda. Diferencie falha do frontend, do contrato, do provider, do banco local e de implantação.
>
> **Depois, corrija por camadas e com inteligência explicável.**
>
> - **B3 determinístico:** permanece autoridade para cotações, históricos, indicadores, carteira, opções, custos e proveniência. Corrija bugs de cálculo, unidade, corte, alinhamento de datas e contrato; não mova cálculo financeiro para o LLM.
> - **João / síntese:** deve ler todo o contexto admissível já armazenado — carteira completa, caixa quando conhecido, ações e opções abertas, histórico pessoal elegível, mercado, fundamentos e notícias/eventos — e explicar como isso muda a decisão. Não pode preencher lacunas com invenções nem substituir os fatos determinísticos. Toda afirmação relevante deve apontar evidência/fonte/data ou ser marcada como hipótese.
> - **Dados insuficientes:** separar ausência de cobertura da fonte, histórico insuficiente, incompatibilidade entre métricas, dado fora do corte e falha de serviço. Exibir uma lacuna única e útil com motivo/impacto e próxima evidência necessária; não despejar 18 linhas repetindo “não comparável”.
> - **Português claro:** começar por síntese curta; usar linguagem operacional e explicar siglas. Em cada alternativa, mostrar fatores a favor, contra, impacto de carteira/capital, condição que mudaria a decisão e grau de confiança. Nunca declarar recomendação automática de ordem.
>
> **Critérios de qualidade por tela**
>
> **Opportunities**
> - Mostrar ranking explicado e estável, com ação/estratégia, capital necessário, prêmio/retorno quando calculável, liquidez, risco/atribuição, compatibilidade com carteira, evidência histórica pessoal pertinente, fatores favoráveis/contrários e lacunas.
> - Não sugerir PUT sem caixa/margem elegível conhecida; não sugerir CALL coberta sem quantidade elegível de ações; considerar concentração e opções existentes; não confundir prêmio bruto com resultado líquido.
> - Deixar evidente por que cada candidata ficou acima/abaixo das demais. Se o backend não suporta ranking com qualidade, indicar o que falta no contrato em vez de gerar pontuação fictícia.
>
> **Strategy Lab**
> - Para ITUB4 × BBDC4, comparar janelas históricas comuns com datas inicial/final comuns, retornos comparáveis e risco realizado, explicando que passado não é previsão. Validar ajuste por proventos/desdobramentos e declarar a metodologia.
> - Usar apenas fundamentos economicamente adequados e comparáveis para bancos; mostrar datas, unidades, período, fonte e qualidade. Classificar corretamente razões, múltiplos, percentuais e valores monetários. Se cobertura for assimétrica, apresentar contagem e motivo por ativo, destacar apenas pares comparáveis e recolher campos individuais num detalhe expansível.
> - Com R$ 10.000 e preço corrente, calcular quantidade indicativa antes de custos apenas se a semântica deixar isso claro; não inventar taxas nem apresentar residual líquido falso. Se não houver premissa de futuro, esconder tabela de payoff vazia e explicar como inserir cenários. Oferecer cenários hipotéticos editáveis claramente separados dos dados observados.
> - A síntese final deve responder “o que favorece ITUB4?”, “o que favorece BBDC4?”, “qual risco pode inverter a comparação?” e “o que impede uma preferência?”. Só declarar vencedor condicional se os dados suportarem; caso contrário, explicar a evidência decisiva ausente.
>
> **Market Intelligence**
> - Integrar gráfico e retornos, RSI/SMA/MACD/volatilidade/drawdown com conclusão em português: estado observado, horizonte, concordância/divergência dos sinais, níveis/situações que invalidam a leitura. Indicador isolado não é sinal de compra/venda.
> - Mostrar notícias e eventos com título, fonte, data de publicação, data do evento, ticker impactado, relevância, direção/ambiguidade, evidência e link. Diferenciar “busca não executada”, “sem evidência encontrada” e “evidência fora do corte”.
> - Interpretar fundamentos e valuation somente com métricas e research qualificadas. Contextualizar fatos corporativos/setoriais e macro com ligação explícita a PETR4 e ao horizonte.
> - Integrar a carteira: posição em PETR4 e CALL vendida devem alterar análise de exposição, alternativas, risco de exercício/rolagem e custo de oportunidade. Reconciliar quantidades por fonte/data ou marcar a divergência; não concluir “manter” sem explicar exposição/condições.
>
> **Validação e conclusão obrigatórias**
>
> 1. Criar testes de regressão para os bugs comprovados: corte São Paulo/UTC, unidades fundamentais, janelas históricas e datas iguais, cobertura assimétrica de fundamentos, interpretação integrada com posição/opções e renderização para ausência de cenários/news.
> 2. Rodar testes backend afetados, build React, verificações de renderização e smoke tests nos três casos. Não afirmar que está “pronto para testar” se o backend ativo ainda não recebeu a versão. Registrar comandos de atualização separados para Windows (frontend) e Ubuntu (serviço `b3-runtime.service`) quando necessário.
> 3. Fazer verificação visual das telas e comparar com os critérios acima. Guardar exemplos de resposta antes/depois, tempos de execução e limitações.
> 4. Concluir com: causas-raiz confirmadas, arquivos/commits alterados, testes com resultado, serviços que precisam ser atualizados, roteiro curto para Edmilson testar e quaisquer lacunas que dependam de provider ou configuração.
>
> Trabalhe em blocos grandes, preserve a arquitetura V4.3 e evite uma refatoração ampla sem evidência. Resolva o que for comprovável no código; não encerre apenas com um plano ou com perguntas que possam ser respondidas inspecionando o repositório/runtime. Se uma dependência externa impedir uma parte, conclua as demais e identifique precisamente a dependência.

## Sequência recomendada para amanhã

1. Abrir o repositório e confirmar branch/HEAD em Windows e Ubuntu; verificar health/build do serviço.
2. Coletar reproduções sanitizadas dos três casos e comparar payloads com o frontend.
3. Corrigir primeiro dados/corte/unidades/contratos; depois síntese e hierarquia das telas.
4. Rodar testes focados e walkthrough visual.
5. Atualizar backend Ubuntu e frontend Windows em separado; confirmar versão ativa antes do teste final do usuário.
