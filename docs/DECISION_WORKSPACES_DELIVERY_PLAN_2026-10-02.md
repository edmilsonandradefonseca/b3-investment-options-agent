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
| B — Comparação econômica | Comparar ativos, strikes/vencimentos e manter/reduzir/comprar com objetivo, horizonte, tamanho, capital e cenários compatíveis | Próximo bloco. Reusar StrategyComparison/AssetEvidencePack; determinar explicitamente dados essenciais e opcionais; mostrar trade-offs, custo de troca e impacto antes/depois. Não inventar retorno esperado ou pesos. |
| C — Opportunities dentro/fora | Universo explícito de carteira + candidatos/watchlist, elegibilidade e ordenação explicável por objetivo | Falta ranking econômico no live path: DEFERRED_INCOMPLETE_CONTEXT. Implementar política determinística versionada; permitir ranking sem componente de experiência quando os demais dados exigidos forem válidos; mostrar exclusões e empates/incomparabilidade. |
| D — Market Intelligence/Copilot | Evidências compartilhadas, fundamentos, alvos com instituição/data/horizonte, eventos, riscos e investigação das comparações | Research compartilhado avança neste bloco; alvos estruturados, cobertura de lacunas por tipo e fechamento dos fluxos continuam abertos. Nenhum alvo é inferido de snippet ou consenso sem população definida. |
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
| AC-15 Lab | PUT VALE3 para 16/10: quais strikes? | Contratos listados, bid/ask/mid, prêmio, delta/IV quando disponíveis, liquidez, breakeven e capital; economia/chain parcial existente, seleção aberta. |
| AC-16 Lab | Risco de exercício da PUT 67,14? | Estimativa ITM no vencimento com modelo/premissas; tocar strike, assignment antecipado e frequência pessoal separados; delta não vira probabilidade autoritativa. |
| AC-17 Lab | Comparar PUTs 67,14/66,64/65,64? | Mesmo as-of, prazo e tamanho; prêmio/capital, breakeven, stress, liquidez e estimativas válidas; identificação real dos contratos exigida. |
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

Próximo bloco: B, comparação econômica sob objetivos/restrições; prioridade de
ranking e comparação corrigida pelo usuário prevalece sobre iniciar nova
persistência de aprendizagem. UC-07/08/09 avançam sem travar decisões correntes.

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
