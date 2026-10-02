# Plano de conclusão funcional — Opportunities, Market Intelligence, Strategy Lab e Copilot

## Objetivo e autoridade

Este plano incorpora as correções do usuário em 02/10: comparar oportunidades
**dentro e fora da carteira**, escolher PUTs conforme objetivo/risco/retorno e
comparar manter uma posição com vendê-la para financiar outra. Reaproveitar os
stores existentes antes de buscar lacunas; apresentar fontes, datas, cálculos,
cenários e conclusões condicionais. O arquivo fornecido de VALE3/RENT3 é referência
de conteúdo e critérios, não fonte de valores atuais ou probabilidades validadas.

Autoridades: restart/handoff, ARCHITECTURE_V4.3, USE_CASES_INVESTMENT_OPTIONS_V2.0,
traceability, FRONTEND_FUNCTIONAL_SPEC, WORK_PROMPT/DECISION_INTELLIGENCE_REVIEW e
ADR-0020/0021. HEAD pré-código `8882636`, PR #66 aberto/draft, CI #1280 SUCCESS.
Nenhum redesenho V4.3, cálculo financeiro no React, ordem de corretagem ou ledger
paralelo. Inventários SQLite/registry e validadores históricos já concluídos não
serão repetidos.

**Numeração:** os 25 exemplos recebidos são critérios AC-01…AC-25, não renomeiam
UCs da arquitetura. UC-03 = Opportunities, UC-04 = Strategy Comparison,
UC-05/06/10 = Market Intelligence; UC-07 = reconstrução histórica, UC-08 =
aprendizagem, UC-09 = precedentes; UC-12 = decisão assistida/Copilot.
UC-07/08/09 enriquecem o produto. Ausência de amostra pessoal não deve bloquear
uma análise econômica fundamentada: seu componente histórico fica indisponível.
Não usar desconhecidos como zero, nem aceitar uma comparação sem dados essenciais.

## Sequência de entregas e aceite

| Bloco | Entrega funcional | Aceite / estado |
| --- | --- | --- |
| A — Contexto e research existente | SQLite de carteira/execuções já ligado; consultar notícias Qdrant e relações de eventos Neo4j antes da busca externa, para cada ativo explícito e IBOV | Este bloco implementa a parcela **research**. Fontes/datas/origem, exclusões, busca só quando não há evento recente admissível ou refresh explícito. Não conclui toda cobertura de informação/valuation. |
| B — Comparação econômica | Comparar ativos, strikes/vencimentos e manter/reduzir/comprar com objetivo, horizonte, tamanho, capital e cenários compatíveis | **Parcial:** B1 calcula payoffs em choques do usuário; B2 permite ranking condicional maximin em base de capital conhecida; B3A compara PUTs exatas do mesmo vencimento numa leitura única da cadeia. Modelo de P(ITM)/P(touch) não calibrado; faltam restrições econômicas completas e custos/troca. |
| C — Opportunities dentro/fora | Universo explícito de carteira + candidatos/watchlist, elegibilidade e ordenação explicável por objetivo | Continua aberto. Falta ranking econômico no live path: DEFERRED_INCOMPLETE_CONTEXT. Implementar política determinística versionada; permitir ranking sem componente de experiência quando os demais dados exigidos forem válidos; mostrar exclusões e empates/incomparabilidade. |
| D — Market Intelligence | Evidências compartilhadas, fundamentos, alvos com instituição/data/horizonte, eventos e riscos | Research compartilhado avança neste bloco; alvos estruturados, cobertura de lacunas por tipo e fechamento dos fluxos continuam abertos. Nenhum alvo é inferido de snippet ou consenso sem população definida. |
| E — UC-07/08/09 | Desfechos comprovados, contexto PIT, experiência persistente e precedentes comparáveis | Execuções observadas e ligação exata já funcionam; desfechos elegíveis reais = 0. Owner canônico de produção e fatos terminais/PIT ainda faltam. Não bloquear B/C/D por esses gaps; não promover Qdrant/Neo4j a owner econômico. |
| F — Aceite ponta a ponta | Executar os casos abaixo via telas/APIs e dados reais | CI e fixtures provam comportamento, não conclusão funcional real; registrar cada aceite e dependência externa separadamente. |

## Matriz de 25 casos do usuário

Todos os casos financeiros permanecem **abertos para aceite ponta a ponta**.
“Parcial” abaixo identifica peças existentes; não é PASS do cenário completo.

| ID / tela | Pergunta de aceite | Resposta exigida / principal gap restante |
| --- | --- | --- |
| AC-01 Opportunities | Melhor compra entre VALE3, RENT3, VIVT3 e BBAS3? | Mesmo horizonte/objetivo; preço, valuation/alvos válidos, tendência, volatilidade, liquidez, risco e razões; ranking econômico aberto. |
| AC-02 Opportunities | Onde alocar R$50 mil entre candidatos? | Carteira/capital atuais, concentração, lotes e alternativas de alocação; otimizador/política de alocação aberta. |
| AC-03 Opportunities | Comprar RENT3 agora ou esperar? | Entrada imediata versus níveis comprovados e cenários; metodologia dos níveis e objetivo explícitos. |
| AC-04 Opportunities | Aumentar VALE3 ou comprar outra ação? | Candidato externo + risco marginal e concentração; comparação econômica aberta. |
| AC-05 Opportunities | Qual posição tem maior desconto ao alvo? | Alvo, fonte, data, horizonte, dispersão e preço comparável; loader estruturado de alvos aberto. |
| AC-06 Opportunities | Qual posição vender para comprar RENT3? | Alternativas sell-to-buy, capital liberado, custos/impostos quando conhecidos, dividendos e custo de oportunidade; fluxo financiado aberto. |
| AC-07 Opportunities | Vender VALE3/comprar RENT3 ou manter? | Antes/depois, caixa, concentração, cenários e custo da troca; duas pernas ligadas, sem assumir caixa grátis. |
| AC-08 Market | Qual alvo de RENT3? | Instituições, datas, horizonte, mediana/mínimo/máximo sobre população válida/deduplicada e upside; valores ausentes indisponíveis. |
| AC-09 Market | Por que VALE3 caiu? | Research existente/complementar rastreável + preços/volume; causalidade interpretativa distinguida dos fatos. Research avança em A. |
| AC-10 Market | Suportes/resistências de RENT3? | Níveis de histórico armazenado, método, janela e data; nunca extrair número sem origem. |
| AC-11 Market | VALE3 mais volátil que o normal? | HV/EWMA/IV e amostra/janelas; IV Rank/Percentile somente com série histórica de IV adequada. |
| AC-12 Market | Faixa de VALE3 até 16/10? | Expected move/distribuição com modelo, prazo, spot e volatilidade; faixa probabilística não é previsão garantida. |
| AC-13 Market | Eventos de RENT3 nas próximas semanas? | Agenda com datas dos eventos e disponibilidade das fontes; notícia recente não prova ausência de eventos futuros. Research A é parcial. |
| AC-14 Market | Meu risco se VALE3 cair 10%? | Posições reais, ações/opções, método full revaluation ou aproximação delta indicada; dados essenciais desconhecidos impedem total completo. |
| AC-15 Lab | PUT VALE3 para 16/10: quais strikes? | Contratos listados e explicitamente selecionados, bid/ask/mid, prêmio, delta/IV quando disponíveis, liquidez, breakeven e colateral; chain agora é comparável, aceite live ainda pendente. |
| AC-16 Lab | Risco de exercício da PUT 67,14? | P(ITM) e P(touch) modelados em campos distintos, sem calibração; assignment antecipado exige estilo confiável e não é estimado; frequência pessoal permanece UNKNOWN sem desfechos comparáveis. |
| AC-17 Lab | Comparar PUTs 67,14/66,64/65,64? | B3A compara IDs exatos do mesmo vencimento/as-of, bid, spread, IV/Greeks, liquidez, break-even, colateral e cenários do usuário. IDs live, sizing comum e aceite ponta a ponta seguem pendentes. |
| AC-18 Lab | Vender PUT VALE3 ou RENT3? | Objetivo, vontade/capacidade de receber ação, exposição e critérios compatíveis; ranking entre ativos aberto. |
| AC-19 Lab | RENT3 a R$35: resultado da minha PUT? | Strike, quantidade e prêmio reais; payoff no vencimento separado de recompra antes do vencimento e custos conhecidos. |
| AC-20 Lab | PUT ITM: aceitar, recomprar ou rolar? | Fechar pelo ask, eventual entrega e roll ligado com crédito/débito, novo capital/risco; assignment não presumido; gestão completa aberta. |
| AC-21 Histórico transversal | Quantas PUTs exercidas/expiradas/roladas em seis meses? | Contagens só de desfechos comprovados, denominador elegível, desconhecidos e cobertura; UC-07 real aberto. |
| AC-22 Histórico transversal | Teria sido melhor comprar PETR4 ou vender PUT? | Histórico realizado separado de contrafactual/backtest, mesmas restrições/custos/PIT e viés; não rotular simulação como experiência real. |
| AC-23 Histórico transversal | Meu percentual de exercício nesse delta/prazo? | Snapshots reais de entrada, comparáveis elegíveis, amostra/confiança/seleção; não probabilidade do mercado. UC-08/09 real aberto. |
| AC-24 Capital transversal | Quantas PUTs com R$60 mil e limite de concentração? | Reserva/capital e todas posições/obrigações, cobertura cash-secured e lote; dimensionamento com limites explícitos. |
| AC-25 Stress transversal | VALE3 -10%, RENT3 -15%, todas PUTs exercidas? | Caixa/posições/exposição/perda antes/depois, prêmios sem duplicação e hipóteses de assignment explícitas; stress conjunto aberto. |

Aceite adicional solicitado nesta conversa: **AC-26 — manter ASAI3 versus vender
ASAI3 e comprar Embraer**, com símbolo resolvido de fonte válida, duas pernas,
capital, custos, riscos, fundamentos e horizonte compatível. O ticker literal
EMBR3 dos exemplos de teste é uma fixture de identificação; não afirma identidade
negociável atual ou cotação real. Resolver nomes/símbolos atuais é gate do fluxo.

Critérios adicionais propostos na revisão de 02/10:

- **AC-27 — continuidade de workspace:** iniciar a decisão em Opportunities e
  avançar para Market Intelligence e Strategy Lab sem redigitar os ativos,
  objetivo, horizonte, capital ou cenário disponíveis; preservar `as_of`,
  fontes/proveniência e desconhecidos. Este fluxo ainda não está implementado.
- **AC-28 — orquestração decisória do Copilot:** perguntar “Tenho R$80 mil;
  compare comprar VALE3, vender PUT de VALE3 e vender PUT de RENT3 para 16/10”.
  Identificar as três alternativas, buscar carteira/capital/evidências de ambos
  ativos e contratos da data, normalizar horizonte/capital, mostrar cálculos,
  cenários e probabilidades somente se houver base válida, citar fontes e
  permitir continuar no Strategy Lab. O fluxo transversal ainda está aberto.

No **AC-16**, assignment antecipado exige estilo de exercício do contrato quando
essa informação for necessária e estiver disponível. Sem estilo/termos de
exercício confiáveis, essa parcela deve ser `UNKNOWN`; probabilidade ITM no
vencimento, P(touch), assignment antecipado e frequência pessoal permanecem
métricas distintas.

Golden cases VALE3/RENT3 usarão contratos realmente disponíveis no as-of do teste.
Números dos anexos são seeds/expectativas de formato, não dados atuais confiáveis.
Cada afirmação quantitativa: fato de fonte, cálculo determinístico ou interpretação
identificados; data/source lineage; ausência UNKNOWN; posição real para “meu risco”.

## Bloco A implementado nesta entrega

- Reusa metadados existentes da coleção B3 `b3_evidence_768_hybrid`, 768d,
  dense+sparse/RRF, filtros exatos ticker/topic=news e verificação local PIT.
  Coleção ausente permanece indisponível; leitura não cria coleção/constraint.
- Neo4j consulta somente B3Entity, instrumento exato e relações diretas de eventos
  IMPACTS/AFFECTS/ABOUT, com disponibilidade e validade. Learning/Outcome de memória
  não é admitido como dado econômico. Backends degradam independentemente.
- Publication/retrieved timestamps obrigatórios; janela de 48h para **research
  corrente**, não regra de validade de learnings antigos. Exclui fontes não
  qualificadas, futuro, validade inválida, outros tickers e chunks sem headline.
- Mesma fonte projetada duas vezes conta uma vez; conflitos de headline/data
  permanecem lacuna. Research recente encontrado não garante cobertura completa,
  alvo atualizado, agenda exaustiva ou ausência de risco.
- Modos `stored_first` (default), `stored_only`, `refresh` explícitos no controle
  “Notícias e eventos”. São modos de **research**, não offline de toda análise:
  cotações/fundamentos/chain continuam com os adapters existentes. Corte histórico
  explícito desabilita coleta de research externo; isso não conclui replay dos
  outros dados do workspace.
- SQLite/carteira/histórico existentes preservados. O painel compartilhado mostra
  fontes, datas, origem, backends e exclusões nas três telas/Copilot contextual.
  Tickers explícitos da pergunta entram no contexto, mesmo externos à carteira;
  isso não substitui resolver nomes de empresas ou toda orquestração de intenções.
- Market Intelligence obtém research armazenado progressivamente pelo novo endpoint
  e deixa a coleta complementar para o fluxo integrado, evitando duas coletas web
  paralelas na inspeção do ativo. Não promete coalescing/reuso entre requests
  independentes, nem redução de latência medida.
- Endpoint `/intelligence/research-context?ticker=RENT3` somente leitura de research,
  sem web/quotes/senior. O endpoint legado `/research/news` permanece coleta explícita.
  Este bloco não grava novos resultados na memória; ingestão/projeção existente
continua responsável por persistência/atualização.

## Bloco B1 implementado — cenários explícitos

- Strategy Lab envia até nove choques percentuais definidos pela pessoa usuária
  e uma data/horizonte comum. A política `terminal-price-scenarios-v1` calcula
  P&L terminal determinístico para compra/posição mantida/reduzida, PUT
  cash-secured e CALL coberta sobre os contratos e posições existentes.
- Opções só recebem payoff quando a data coincide exatamente com vencimento.
  Quantidade/capital/posição ou horizonte incompatível fica indisponível e pode
  tornar o resultado parcial; nunca se marca opção a mercado usando choque como
  se fosse cotação de saída.
- Frontend mostra o P&L por cenário e limitações. Choques não recebem
  probabilidade, retorno esperado ou ranking automático. Nenhum aprendizado
  pessoal não validado entra no cálculo.
- Ainda não cobre objetivo/restrições que ordenem alternativas, varredura
  comparável de cadeia/strikes, custos/impostos, caixa e duas pernas financiadas
  sell-to-buy. O caso ASAI3→Embraer permanece pendente da resolução do ticker e
  das duas pernas econômicas. Oportunidades continua sem ranking live.
- Verificação local: 791 testes Python, TypeScript/Vite build e diff check PASS;
  GitHub CI #1282 PASS no commit `f8f975f`. Aceite Ubuntu/desktop ainda pendente.

Matriz: Strategy Lab passa de “cenários não expostos” para **parcial** para
choques fornecidos pelo usuário; os casos AC-15…AC-20 e AC-26 seguem abertos
para aceite real integral. Opportunities permanece como bloco C; UC-07/08/09
seguem informativos e inelegíveis para influenciar a ordenação.

## Bloco B2 — objetivo de cenário condicional

O B2 acrescenta seleção explícita entre comparar sem ranking e maximizar o menor
retorno sobre capital dentro dos choques escolhidos. Usa denominadores declarados
por alternativa: valor de compra, colateral strike×multiplicador, notional das
ações cobertas ou valor corrente conhecido da posição. A ordenação condicional
requer P&L para todos os cenários e base de capital positiva/conhecida nos dois
lados; empate e incomparabilidade continuam explícitos. A política não atribui
probabilidades nem prediz o pior cenário real. Custos/tributos ainda ausentes
limitam a conclusão econômica.

Próxima ordem, atualizada pela revisão de produto: **B3** chain multi-strike e
saídas distintas de P(ITM), P(touch), assignment (com estilo de exercício
verificado) e frequência pessoal; **C** ranking econômico de Opportunities
dentro/fora; **D** alvos estruturados e fundamentos faltantes em Market
Intelligence; **E** sell-to-buy, caixa/custos e stress de carteira; **F** AC-27/28
continuidade e orquestração do Copilot; depois gates UC-07/08/09 e golden cases
VALE3/RENT3 ponta a ponta. Nenhum desses blocos cria persistência por conveniência.
Histórico UC-07/08/09 continua incapaz de alterar ranking sem desfecho elegível.

## Bloco B3A — comparação de PUTs multi-strike

`LiveStrategyComparisonService.compare_put_candidates` aceita de 2 a 20 IDs
exatos escolhidos pela pessoa usuária, exige PUTs do mesmo subjacente e um único
vencimento, e lê uma cadeia OPLAB uma vez por comparação. Exige bid positivo e
quote único por contrato; não completa seleção com strikes vizinhos. Exibe bid,
ask, mid, IV/Greeks disponíveis, spread, volume/OI, prêmio por contrato,
break-even, colateral de strike, perda máxima antes de custos e P&L nos choques
terminais selecionados pelo usuário. A política opcional B2 pode ranquear apenas
o pior retorno sobre colateral dentro desses choques e produz empate ou
indisponibilidade quando a entrada não é completa.

P(ITM) e P(touch) são saídas separadas do proxy lognormal sob medida
risk-neutral, taxa e dividendos iguais a zero. Só calcula quando spot e IV em
unidade decimal são positivos e inequívocos; marca `NOT_CALIBRATED` e expõe os
parâmetros. Não representam probabilidade real de assignment. O estilo do
contrato é exibido como valor reportado pela OPLAB; valor ausente ou não
reconhecido é UNKNOWN. Nenhum risco American de exercício antecipado é modelado.
Frequência pessoal continua UNKNOWN porque esta comparação não recebe amostra
UC-07/08/09 elegível/PIT. Nenhuma saída estimada altera ranking fora do maximin
explícito dos choques do usuário.

Frontend Strategy Lab expõe uma seção específica para escolher vencimento e
marcar contratos da mesma cadeia; requer configuração de PUT em Ativo A para
carregar essa cadeia. Os números dos exemplos VALE3 continuam critérios, não
contratos assumidos como disponíveis. A implementação não fecha AC-15/16/17
sem IDs/quotes reais e validação na instalação Ubuntu.

## Verificação deste bloco

786 testes Python PASS; TypeScript/Vite build PASS; diff check PASS. Os 26 novos
casos de regressão cobrem identidade/tópico exatos, metadata/RRF, timestamps,
fontes, chunks, conflito/deduplicação, disponibilidade independente dos backends,
read-only sem criação de schema, base antes de coleta, fallback por ativo externo,
refresh, modo armazenado, cutoff histórico, API/validação e extração de tickers
explícitos. Casos positivos usam fixtures, não alegam research real disponível.
CI deve ser confirmado no commit publicado; registrar SHA/run no PR.

Aceite real deste bloco, somente após publicação/CI verde: instalar a branch,
reiniciar o serviço e consultar `/intelligence/research-context?ticker=RENT3`.
Conferir o novo controle de research e painel nas telas após atualizar o checkout
Windows. Ausência de eventos ou backend indisponível deve permanecer explícita;
isso não constitui reprovação de ranking nem aceite dos 25 casos financeiros.
Não repetir inventários de storage, lifecycle/history validators ou diagnóstico
OPLAB. Nenhum aceite real completo deste bloco foi recebido ainda.


## Correções de fluxo e preço em Options — 02/10

Implementação publicada no bloco
`docs/OPENCLAW_STDIN_AND_OPTION_ENTRY_PRICE_BLOCK_2026-10-02.md`:

- OpenClaw recebe prompts longos pela entrada padrão (`--message-file -`), sem
  colocá-los no argv ou truncar contexto determinístico.
- Options apresenta preço unitário de aquisição/venda ao lado do preço atual,
  derivado do `average_cost` canônico ou das notas do mesmo contrato quando
  lado e quantidade conciliam com a posição aberta.
- Valor total de abertura continua separado. A nota PCARJ40 (52.000 compradas
  a R$ 0,02, débito R$ 1.040,00) define o aceite.

Build frontend PASS localmente e regressão de prompt longo adicionada; pytest
não está disponível neste sandbox. Esperar CI integral verde antes de pedir
instalação/validação Ubuntu. Em produção validar Options, Opportunities ITUB4
e Strategy Lab ITUB4 × WEGE3. UC-07/08/09 econômicos permanecem em andamento.
