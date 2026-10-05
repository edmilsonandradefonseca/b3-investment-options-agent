# Especificação funcional dos workspaces — V1.2

Data: 05/10/2026. Status: comportamento aprovado pelo usuário; implementação e aceite registrados separadamente.

## Autoridade e continuidade

Este documento é a revisão normativa de Opportunities, Strategy Lab e Market Intelligence da especificação V1.1 (arquivo FRONTEND_FUNCTIONAL_SPEC_V1.0.md), sob ARCHITECTURE_V4.4.md. Não cria uma especificação concorrente: mantém Portfolio, Options, inputs, Copilot e demais invariantes da V1.1. Nos três workspaces prevalecem os requisitos abaixo aprovados em 05/10. Preserva UC-03, UC-04/11, UC-05/06/10 e AC-01–28 do DECISION_WORKSPACES_DELIVERY_PLAN_2026-10-02.md; mudanças de responsabilidade constam da matriz. G01–G12 V4.4 continuam gates operacionais.

A revisão mais recente reduz o escopo automático de Opportunities: descobrir teses sobre ações; opções possuídas entram como exposição. Não varrer cadeias nem calcular rolagens automaticamente. A definição ampla de estratégias da arquitetura permanece no Strategy Lab sob demanda. Não há encaminhamento obrigatório/botão de próxima etapa em Opportunities.

## Requisitos compartilhados

| ID | Entrega e aceite |
|---|---|
| WS-01 | Cinco workspaces principais. Copilot transversal; análises solicitadas nas telas aparecem no painel central. |
| WS-02 | Primeiro conteúdo analítico é a explicação do agente B3: conclusão, argumentos, evidências contrárias, riscos e condições de mudança. Não apresentar digest Qwen como análise financeira completa. |
| WS-03 | Dados/cálculos determinísticos no backend; fatos, hipóteses e interpretação distinguíveis. Fontes/datas por afirmação quantitativa. Não fabricar vencedor, alvo, preço ou probabilidade. |
| WS-04 | Mesma carteira vigente e revisão de dados entre narrativa, tabelas e gráficos. Mudança de snapshot invalida análise atual; notas são aditivas/deduplicadas. |
| WS-05 | LED amarelo + texto durante processamento, verde concluído, vermelho falha. Estado inicial neutro. Cor nunca é o único sinal. Duplo clique não duplica requisição. Conclusão parcial recebe aviso localizado; verde não certifica cobertura total. |
| WS-06 | Reusar dados válidos; background coleta documentos/fundamentos/research, interação atualiza apenas lacunas necessárias. Yahoo → OPLAB → BRAPI nas capacidades de ações; opções OPLAB. Franquia BRAPI 15.000/mês. Timestamp de consulta não substitui timestamp do preço. |
| WS-07 | Não há página separada de dados insuficientes. Lacunas aparecem no campo/ativo afetado. Falha preserva última análise válida identificada como anterior; falha total nunca vira ausência de oportunidades. |
| WS-08 | Retorno fora de ordem não sobrescreve análise nova; mudança de ativo/página preserva isolamento de resultados. Acessibilidade por teclado, foco visível, contraste e desktop 1440×900/1180×720. |
| WS-09 | Sem execução de ordens. Sem dados pessoais ou payloads de carteira nos logs públicos/artifacts de aceite. Identificar build frontend, API, commit checkout e processo ativo separadamente. |

## Opportunities — UC-03

Pergunta: quais ações merecem atenção agora e por quê? Carteira completa + candidatos acompanhados e pesquisa B3; sem teto silencioso de vinte. Não garante varredura simultânea de todas as ações listadas.

### Fluxo O1 — abertura

1. Na abertura da aplicação, carregar snapshot vigente e última análise disponível; identificá-la como anterior enquanto atualiza.
2. Iniciar uma revisão automática por sessão/snapshot, sem depender de abrir a aba e sem duplicar por remontagem React.
3. Atualizar preços das ações relevantes dentro de orçamento de latência; reutilizar evidências coletadas. Não solicitar cadeia de opções.
4. Backend calcula fatos/impactos e agente B3 integra movimentos, fundamentos, resultados, proventos, notícias e exposição. Alta/queda isolada não constitui oportunidade.
5. Publicar resumo e lista selecionada por materialidade, mantendo razão de cobertura por ativo.

### Fluxo O2 — atualização manual

Botão “Buscar novas oportunidades”; amarelo e etapa atual durante execução. Reavalia com dados válidos e atualiza o necessário, sem refresh indiscriminado. Verde ao concluir, inclusive lista vazia fundamentada. Em falha, vermelho e “Tentar novamente”; manter resultado anterior sem relabelar horário.

### Fluxo O3 — seleção

Clicar no item abre detalhe da análise já produzida, sem nova coleta. Primeiro a explicação do agente; depois o que mudou, evidências favoráveis, riscos/argumentos contrários, impacto na carteira, preço/volume e fontes expansíveis. O fluxo termina na leitura. Usuário decide separadamente se deseja aprofundar.

| ID | Entrega e aceite |
|---|---|
| OPP-01 | Executar O1 após carregar carteira; revisão automática e manual não concorrem para a mesma chave. |
| OPP-02 | Lista e detalhe lado a lado; seleção preservada quando item continua presente. Indicadores: possível entrada/aumento, revisar/reduzir, possível realocação, acompanhar. |
| OPP-03 | Resumo do agente + ativos analisados + oportunidades + cobertura localizada. Não usar capital necessário como KPI principal. |
| OPP-04 | Oportunidade exige tese e evidência específica; explicitar por que agora, relevância econômica/risco e efeito da concentração. Critérios de materialidade versionados no backend. Não preencher quota artificial de sugestões. |
| OPP-05 | Lista vazia válida: explicar por que nenhuma operação relevante foi identificada no universo avaliado e o que justificaria reavaliar. Falha de síntese/coleta não pode produzir essa conclusão automaticamente. |
| OPP-06 | Ações são objeto da descoberta; opções possuídas entram apenas como contexto de exposição/cobertura. Nenhuma chamada de chain no fluxo de abertura. |
| OPP-07 | Item “acompanhar” fica separado das oportunidades de ação material. Alternativa de manter é legítima. Recompra/strike/rolagem não são recomendações automáticas desta revisão. |

## Strategy Lab — UC-04/11, UC-12 contextual

Pergunta: a tese faz sentido e qual alternativa atende melhor ao objetivo?

### Fluxo S1 — linguagem natural

Campo amplo “O que você deseja analisar?” + exemplos clicáveis de comparação, tese, cenário, estratégia e posição. Botões Analisar/Nova análise e LED. Pergunta livre é entrada principal; controles estruturados são opcionais e não contaminam pergunta com ITUB4/BBDC4 ou R$10 mil default.

Identificar ativos, posições, objetivo, horizonte e alternativas do texto/contexto. Mostrar entendimento. Se faltar informação indispensável, pedir uma pergunta específica no painel central; não impor confirmação quando claro. Hipótese do usuário permanece hipótese, nunca fato coletado.

### Fluxo S2 — resposta

Primeiro análise do agente B3: avaliação, preferência se fundamentada, contrapontos, risco e condições de mudança. A seguir comparação objetiva e efeito sobre carteira completa. Dados progressivos não podem ser apresentados como síntese concluída. Preservar fatos se síntese falhar.

Para ação×ação: fundamentos setoriais comparáveis, valuation, perspectivas/proventos, histórico comum, preço/quantidade e exposição. Para ações/opções/múltiplas pernas: contratos exatos, lados, quantidades, capital, cobertura, bid/ask, custos, payoff e caixa antes/depois. Incluir manter como referência quando aplicável. Não multiplicar por 100 sem identidade/unidade do contrato.

Separar resultado acumulado de efeito incremental; crédito de rolagem não equivale a lucro. Quantidade/resultado bruto antes de custos pode ser mostrado quando custos desconhecidos, com líquido indisponível. Não declarar perda máxima finita para estratégia com perda ilimitada.

### Fluxo S3 — cenários e continuação

Sem hipóteses não desenhar tabela vazia; “Adicionar cenário” expande. Cenários editáveis são hipóteses, não previsões; payoff no vencimento não é marcação antes do vencimento. Campo “Ajustar ou aprofundar esta análise” no painel central mantém pergunta, respostas e premissas por revisão. Recalcular cria versão, não reescreve silenciosamente histórico.

| ID | Entrega e aceite |
|---|---|
| LAB-01 | Pergunta natural chega ao backend sem defaults ocultos; ambiguidade essencial retorna esclarecimento central. |
| LAB-02 | Explicação sênior primeiro; resultado completo no centro, não somente no Copilot. |
| LAB-03 | Tabela/gráficos adaptam ao tipo de decisão; ações: histórico normalizado e concentração; opções: payoff/fluxos e contratos. |
| LAB-04 | Carteira completa antes/depois, posições mantidas, capital comprometido e obrigações incluídos; manter como referência pertinente. |
| LAB-05 | Cenários explícitos, metodologia/custos conhecidos, contratos verdadeiros; não inventar comparação numérica quando faltam entradas essenciais. |
| LAB-06 | Continuação central preserva contexto e revisões; Nova análise limpa só a sessão do Lab. |
| LAB-07 | Só buscar cadeias/cotações de opções quando a pergunta/estratégia exigir. Reutilizar research válido. |

## Market Intelligence — UC-05/06/10

Pergunta: o que mudou, por que importa e como afeta minha exposição?

### Fluxo M1 — panorama

Ao entrar, apresentar panorama e explicação B3 antes dos indicadores. Mercado/macroeconomia, setores, exposição consolidada, agenda e notícias prioritárias. Relacionar fatores disponíveis (índices, juros, câmbio, commodities) a posições, sem tratar correlação como causalidade. Atualizar análise explicitamente por botão e LED; usar dados válidos em background.

### Fluxo M2 — ativo

Pesquisar ação/empresa com resolução determinística; ticker externo à carteira é válido. Mostrar análise B3 primeiro, seguida de preço/volume, fundamentos, valuation/research, dividendos/JCP, notícias/eventos e minha exposição. Gráfico 1S/1M/3M/6M/1A/máximo. Avisar janela parcial sem inventar candles; separar bruto/ajustado consistentemente.

### Fluxo M3 — opções sob demanda

Posições possuídas participam do contexto sem carregar cadeia inteira. Abrir seção de opções busca contratos relevantes, bid/ask, liquidez, IV/Greeks disponíveis. Ausente não é zero. Estatísticas/superfícies só com amostra apropriada.

| ID | Entrega e aceite |
|---|---|
| MI-01 | Panorama interpretado com mercado, setores e impacto na carteira; não somente lista de indicadores. |
| MI-02 | Análise do ativo aparece antes do gráfico; narrativa conecta resultados, preço, expectativas e riscos, distinguindo fato de interpretação. |
| MI-03 | Horizontes de gráfico e fundamentos organizados em resultado/balanço/caixa/múltiplos/proventos; unidades e períodos econômicos explícitos. |
| MI-04 | Alvos individuais: instituição/data/horizonte/fonte; consenso Yahoo separado, com população quando conhecida. Não extrair alvo de snippet sem evidência. |
| MI-05 | Agenda separa confirmado/estimado; notícia vazia não prova ausência de evento. |
| MI-06 | Exposição conjunta de ações e opções; chain só sob demanda; nenhuma ação de corretagem. |

## Contrato funcional mínimo backend → frontend

Reusar /v1/orchestrate e serviços existentes. Evoluir contratos versionados quando necessário; não criar um segundo ledger. Resposta deve transportar: identificador da análise, revisão da carteira, as_of, fontes/observações, estado de processamento, narrativa, fatos/calculados, hipóteses, alternativas, razões, cobertura por ativo, erros localizados e status da síntese. Opportunities exige lista material filtrada e justificativa por item; Lab exige pergunta/contexto/revisão; Market exige escopo panorama/ativo. Ausência de um campo é gap, não licença para inferi-lo no React.

## Rastreabilidade e alterações dos critérios existentes

| Critérios existentes | Requisitos novos / interpretação vigente |
|---|---|
| AC-01/03/04/05 | OPP-02/04, MI-02/04; discovery de tese, comparação detalhada no Lab por iniciativa do usuário |
| AC-02/06/07/26 | LAB-01/03/04; alocação/troca financiada preservadas como demanda explícita, não automatizadas na abertura |
| AC-08–14 | MI-01–06; stress numérico explícito também LAB-05 |
| AC-15–20 | LAB-03/05/07, opções sob demanda |
| AC-21–23 | Contexto histórico preservado V1.1; sem amostra não contam como probabilidade ou fator de ranking |
| AC-24/25 | LAB-04/05 e WS-03, capital/stress completos |
| AC-27 | Contexto transversal preservado WS-04/08; encaminhamento obrigatório e CTA Opportunities→Lab retirados pela aprovação de 05/10 |
| AC-28 | LAB-01/02/06 e Copilot transversal; resposta pedida no Lab permanece no centro |
| G01–G12 V4.4 | Gates continuam; execução automática ampla de opções em Opportunities substituída por OPP-06 |

IDs AC/UC antigos não são renumerados. Tests e gaps referenciam IDs desta matriz. Portfolio/Options e capacidades históricas fora do escopo mantêm V1.1.

## Aceite e entrega

Casos: abertura/refresh sem chain, zero oportunidades fundamentado, falha parcial/total, carteira >20 ativos; ITUB4×BBDC4 R$10 mil; tese PETR4 com hipótese de queda; PUT versus ação; manter/encerrar/rolar contratos reais; pergunta ambígua; continuação; panorama e pesquisa externa; alvos versus consenso; mudança de snapshot e resposta fora de ordem.

Cada aceite registra commit código, build frontend, processo/versão API, request sanitizado, campos entregues, tempo por estágio e evidência visual 1440×900 e 1180×720. Fixture prova contrato; runner Ubuntu prova apenas o processo testado; preview Ubuntu não prova instalação Windows. Não declarar pronto com base só em build.

Plano e achados vivos: FRONTEND_V44_GAPS_AND_DELIVERY_2026-10-05.md. Especificação define esperado; esse registro define observado, correção e aceite.

## Referências de implementação fixadas

- [V1.1, arquivo V1.0](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/blob/5ccb458cf81fa3cb2f5f1c3d7f30bb7fd4bace9e/docs/FRONTEND_FUNCTIONAL_SPEC_V1.0.md).
- [Critérios AC-01–28](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/blob/5ccb458cf81fa3cb2f5f1c3d7f30bb7fd4bace9e/docs/DECISION_WORKSPACES_DELIVERY_PLAN_2026-10-02.md).
- [Arquitetura V4.4 em main](ARCHITECTURE_V4.4.md).

