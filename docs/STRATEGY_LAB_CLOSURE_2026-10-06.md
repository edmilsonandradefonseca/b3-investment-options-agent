# Fechamento do Strategy Lab — execução de 06/10/2026

Este é o plano de entrega de UC-04/11 sob a especificação normativa `FRONTEND_DECISION_WORKSPACES_SPEC_V1.2.md`. Reutiliza LAB-01–07 e AC-01–28; não substitui requisitos nem cria outra especificação. Opportunities permanece no escopo já aceito.

## Linha de base aceita

Compra ITUB4 × BBDC4, R$ 10 mil: entrada natural, corte interativo corrigido, 274 sessões comuns, cálculo bruto com conservação do orçamento e síntese sênior na API ativa. Gate 37462396255 passou depois do reinício de 09h17 BRT. Walkthrough 37446374999 passou. Isso não fecha todo o Lab.

## Cinco entregas para o fechamento

| Ordem | Entrega | Lacuna comprovada no código | Critério de conclusão |
|---|---|---|---|
| 1 | Entender a pergunta e selecionar a posição — LAB-01/06/07 | Parser natural só promove dois padrões de compra de ações. Pedidos genéricos de encerrar/rolar seguem para raciocínio sem um contrato selecionado. | Mostrar intenção e premissas reconhecidas; pedir apenas entradas essenciais ausentes. Vincular o código à posição vigente quando a operação usar posição existente. Não adivinhar contrato, vencimento, quantidade, objetivo ou choque. Continuação resolve a pergunta, sem transformar resposta antiga em cotação atual. |
| 2 | Modelo de alternativas e pernas — LAB-03/05/07 | `StrategyComparison` exige duas alternativas; opções em `strategy_live.py` usam `contract_count=1`. | Suportar manter/encerrar/rolar na mesma comparação e representar cada perna: contrato, lado, quantidade, multiplicador verificado e fonte/data. Quantidade da posição e unidade negociada são distintas. Compatibilidade da comparação entre duas ações preservada. Consultar somente cadeias necessárias, reutilizando snapshot admissível. |
| 3 | Motor de operações e cenários — LAB-03/05 | A comparação live aceita BUY_STOCK/HOLD/SELL_STOCK/SELL_PUT/SELL_CALL coberta; não há execução canônica de encerramento e rolagem nessa entrada. | Comparar ação × PUT, manter × CALL coberta e manter × encerrar × rolar uma posição real. Compra/recompra usa ask admissível; venda usa bid admissível. Separar fluxo incremental, resultado acumulado conhecido e custos. Crédito de rolagem não vira lucro. Cenários terminais são hipóteses explícitas; prazo diferente não vira payoff comum antes do vencimento. Sem preço executável/identidade/cobertura, explicar a dependência e conservar UNKNOWN. |
| 4 | Carteira antes/depois e tela central — LAB-02/03/04/06 | Evidência por ativo não equivale a projeção completa de todas as posições, caixa e obrigações de cada alternativa. | Preservar todas as posições não alteradas; recalcular caixa conhecido, colateral, cobertura livre após CALLs já vendidas e obrigações. Não reutilizar a mesma cobertura para duas vendas. Tabela e gráfico usam números do backend. Síntese sênior explica vantagens, contrapontos, preferência condicional e invalidação. Versões e fontes permanecem visíveis. |
| 5 | Aceite completo em dados reais — LAB-01–07, gates existentes | Aceite atual cobre duas ações e PETR4, não todas as operações. | Testes de conservação e cobertura, candidato real, instalação/reinício quando necessário, gate HTTP ativo e walkthrough dos casos abaixo. Marcar o Lab completo apenas quando cada caso tiver evidência aprovada, com limitações das fontes registradas. |

## Casos obrigatórios do último gate

1. Regressão ITUB4 × BBDC4 com R$ 10 mil: mesma entrada natural, orçamento e janelas comuns; sem vencedor inventado.
2. Comprar ação versus vender PUT: contrato verdadeiro, quantidade explícita, colateral, prêmio bruto, risco e cenário de exercício.
3. Manter ação versus vender CALL coberta: incluir cobertura já comprometida e perda da alta; rejeitar quantidade descoberta.
4. Manter/encerrar/rolar uma opção efetivamente aberta: contrato antigo exato, contrato novo selecionado, quantidade parcial/integral e custos conhecidos/desconhecidos. Mostrar as três alternativas e as posições que ficam.
5. Hipótese de queda: usuário fornece horizonte e choque; payoff terminal rotulado como hipótese, sem inventar prêmio de mercado futuro.
6. Pedido ambíguo e esclarecimento: nenhuma consulta de cadeia antes de identificar o contrato; resposta central e continuação.
7. Carteira alterada, resposta fora de ordem, falha de fonte ou síntese, nova tentativa e Nova análise: preservar versões e fatos; não reutilizar snapshot anterior como posição vigente.

## Incremento em implementação

Primeira correção da entrega 1: pedidos genéricos de encerrar/rolar/vender uma opção sem código recebem `NEEDS_CLARIFICATION` no painel central, sem aquisição de cadeia nem chamada sênior. O código fornecido posteriormente ainda precisa ser validado e vinculado à posição pela implementação seguinte; este incremento não afirma fechar LAB-01 inteiro.

O próximo incremento deve ligar a seleção de posição ao snapshot atual e ao modelo de pernas da entrega 2. Não declarar fechamento integral apenas porque a pergunta de esclarecimento funciona.

Seleção implementada no segundo incremento: contrato único no BTG atual, lado e fonte preservados, quantidade explícita em unidades ou posição integral, rejeição de excesso e continuação relendo snapshot. Resposta `INPUTS_IDENTIFIED` conserva cálculo pendente. Identidade/multiplicador do provedor, pernas/alternativas e motor de operações ainda precisam das entregas 2 e 3; não há fechamento integral nem recomendação de ordem.

Aceite do segundo incremento em 06/10 às 11h20 BRT: gate HTTP ativo 37478059021 SUCCESS (reinício, hash e seleção/quantidade no extrato vigente); visual 37471916187 SUCCESS (fixture central e walkthrough real). CI 1008 testes. Quantidades/seleção aceitas; cálculos de encerramento/rolagem continuam pendentes. Entregas 2–5 permanecem abertas.

## Terceiro incremento — CI e visual aceitos; aceite ativo pendente

O backend lê uma cadeia OPLAB atual após validar novamente posição e quantidade no BTG vigente. Sem destino escolhido, retorna contratos do mesmo subjacente/tipo com vencimento posterior e preço executável admissível; o usuário escolhe o destino. O cálculo determinístico monta manter/encerrar/rolar, usa ask em compras/recompras e bid em vendas, mantém unidades e multiplicador por perna, preserva as demais posições e separa fluxo incremental, custos e lucro acumulado desconhecido. O comparativo passa pela síntese sênior padrão no Strategy Lab. A tela central exibe as pernas, fontes/horários, projeções e campos UNKNOWN.

CI 37490393724 passou com 1.019 testes Python, build React e renderização. Walkthrough do runner Ubuntu 37490385165 passou na fixture de rolagem e no cockpit real em 1920/1440/1366; o log registra PASS para esclarecimento, posição, escolha exata do destino e três alternativas.

A execução manual posterior em /opt passou build e renderização, mas falhou na análise 4 antes de exibir PETRK400. Seus nomes de bundles diferem dos gerados pelo runner em 438edef (Node 24 no terminal local, Node 22 no runner), então a revisão do checkout local precisa ser alinhada antes de considerar esse resultado equivalente; a falha local não invalida o walkthrough do SHA testado.

Aceite ativo: a primeira tentativa 37487319451 parou na comparação de hashes. A repetição (job 112402592905) confirmou que os módulos instalados correspondem à revisão, mas falhou porque o processo b3-runtime.service iniciou antes dos arquivos instalados. O gate terminou nessa verificação e não leu o extrato BTG, não consultou OPLAB e não calculou alternativas nessa repetição. É necessário reiniciar o runtime depois da instalação e então repetir o gate. O reinício continua sendo uma ação manual do usuário conforme sua preferência; não foi executado pelo workflow.

Este incremento não fecha o Lab: reconciliação de caixa, obrigações e cobertura completas; cenários com horizonte/choque explícitos; e aceites reais dos outros casos da matriz permanecem abertos. Caixa líquido após operação exige custos conhecidos; lucro acumulado requer histórico; vencimentos distintos não recebem ranking ou payoff comum. Nenhuma ordem é enviada.


## Aceite ativo da rolagem — 06/10/2026, 14h54 BRT

Correções aprovadas pela CI do commit `c882b3648f16506c49c7cf4a85d3fc520f36d7f3`; CI posterior do checkpoint `ea92863b2feef7d16e20df1dd3efaadc2a7318d9` também passou. A suíte Python e o build React estão verdes.

O aceite ativo do runner Ubuntu passou no run `37506783669`, job `112417351823`, revisão `ea92863b2feef7d16e20df1dd3efaadc2a7318d9`:
- `ACTIVE_REVISION_AND_RESTART=PASS`
- `ACTIVE_LAB_CURRENT_POSITION_QUANTITY_ROLL_AND_COMPARISON=PASS`

O gate percorreu o snapshot BTG vigente, encontrou contrato de destino real com cotação OPLAB admissível e concluiu a comparação determinística manter/encerrar/rolar com identidade, quantidade, lado de execução, multiplicador, cotação e fontes. A validação é somente leitura; nenhuma ordem foi enviada.

Causas corrigidas:
1. O Strategy Lab não aceitava um identificador OPLAB exibido como destino se ele não correspondesse ao padrão do parser de códigos digitados. Agora reconhece a identidade exata entre os candidatos apresentados; regressão coberta com identificador fora do padrão tipado.
2. A API definia `derived_synthesis_status` depois de construir `OrchestratorResponse`, que copia o resultado. O campo não chegava à resposta HTTP determinística. A atribuição agora ocorre antes da cópia, validada pelo gate ativo.

Este aceite fecha o incremento de comparação de posição real. **Ainda não fecha o Strategy Lab inteiro.** Permanecem as entregas 4–5: reconciliação integral de caixa/obrigações/cobertura e aceites reais dos outros casos da matriz (PUT vs ação, CALL coberta, cenários explícitos e regressões de carteira/ordem/falha/nova análise). Não declarar o Lab completo até a evidência desses casos ser aprovada.


## Aceite HTTP ativo de Strategy Lab e Market Intelligence — 06/10/2026

O workflow `37507480152`, job `112419706584`, confirmou `ACTIVE_REVISION_AND_RESTART=PASS` e aceitou:
- **Strategy Lab — LAB-01/03/05:** pergunta natural com R$ 10 mil, ITUB4 × BBDC4, duas alternativas e 275 sessões comuns; conservação de orçamento e dimensionamento bruto passaram.
- **Strategy Lab — LAB-02:** síntese sênior sobre a comparação canônica passou (tese e justificativa presentes; 63,34 s).
- **Market Intelligence — MI-02/04/05:** síntese sênior ativa para PETR4 passou (38,96 s); o payload incluiu alvos institucionais e dividendos do emissor.

A aceitação de Market Intelligence é **parcial quanto à evidência**: `institution_targets.status=UNKNOWN_NO_ADMISSIBLE_TARGETS` e `issuer_dividends.collection_status=PROVIDER_UNAVAILABLE`. O sistema expõe essas lacunas sem falhar a resposta, mas ainda falta demonstrar cobertura válida de preço-alvo/dividendos e o conjunto completo de indicadores, eventos e walkthrough visual no runtime.

## Próxima sequência de fechamento

1. Fechar os casos Strategy Lab ação × PUT, CALL coberta, cenário com horizonte/choque explícitos e regressões de carteira/ordem/falha/nova análise; depois completar a reconciliação de caixa, obrigações e cobertura.
2. Em Market Intelligence, investigar a indisponibilidade do provedor de dividendos e a ausência de alvos admissíveis; conferir indicadores, notícias/eventos com fonte/data/impacto e a tela no runtime.
3. Executar a matriz final dos dois espaços com fontes/limitações registradas. Manter status parcial até todos os critérios normativos serem aceitos.

Os aceites desta seção são somente leitura. Nenhuma ordem foi enviada.


## Quarto incremento — cobertura livre de CALL coberta

O Strategy Lab agora desconta do total de ações da carteira as ações já comprometidas por CALLs vendidas antes de aceitar uma nova CALL coberta. Se uma CALL curta existente não tiver subjacente reconciliado, a cobertura livre fica desconhecida e a comparação é recusada. A resposta expõe ações totais, ações já comprometidas, cobertura livre e IDs das posições comprometedoras.

A regressão valida dois casos: 200 ações com 100 já comprometidas deixam exatamente 100 ações livres para uma CALL de multiplicador 100; 100 ações com as mesmas 100 comprometidas não podem ser reutilizadas. O gate também conserva a validação anterior de insuficiência de cobertura.

CI 37510530531 passou: 1.022 testes Python, 13 avisos de dependências e build/renderização React aprovados. Este é aceite de código/CI; o runner Ubuntu instalou a revisão `b37f8b4a1a1d49536ba8a2cf399a191ac6bf2e74` em `/opt/b3-investment-options-agent`, mas o processo ativo ainda não a carregou. O workflow 37510523633 parou antes do restart com `sudo: interactive authentication is required`, e os gates HTTP ativos foram ignorados. O workflow de backend agora inclui `strategy_live.py` e `test_strategy_live.py` nos gatilhos/testes Ubuntu. A ativação continua pendente do restart confirmado pelo usuário e da reexecução do gate.

O Lab permanece parcial. Próximos aceites: ação × PUT; confirmar o cenário com horizonte/choques explícitos no Strategy Lab; reconciliação integral de caixa, obrigações e cobertura da carteira; e regressões de snapshot alterado, resposta fora de ordem, falha de fonte/síntese, retry e Nova análise. Só depois executar a matriz final e marcar o Lab como completo.


## Quinto aceite — ação × PUT e cenários explícitos, 06/10/2026 15h57 BRT

A validação ativa do runner passou no workflow [37515317840](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37515317840), após o usuário confirmar o restart:
- revisão e processo ativo conferidos;
- comparação de posição vigente, quantidade e rolagem continuou aprovada;
- comparação real comprar ação × vender PUT passou com contrato OPLAB explícito, bid positivo e vencimento futuro;
- cenários hipotéticos de -10%, 0% e +10% até o vencimento passaram, sem probabilidades ou ranking;
- nenhuma ordem foi enviada.

A CI do commit `713b30051f08d5798a1a3bf171bd481c2a32d8fa` passou no workflow [37515323818](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37515323818): 1.022 testes Python; build e renderização React aprovados. A seleção do gate foi alinhada aos critérios da rota live de uma PUT explícita: identidade do ativo/contrato, vencimento futuro e bid positivo. Uma tentativa anterior não passou porque o validador adicionava filtros próprios de PIT/qualidade que não são exigidos nesse caminho da rota; isso era um falso negativo do gate, e não uma aprovação de cotação inválida.

O caso ação × PUT e os cenários explícitos estão aceitos. O Strategy Lab segue **parcial**. Próximos gates: CALL coberta real com a cobertura já comprometida; reconciliação integral de caixa/obrigações e demais posições; regressões de snapshot alterado, resposta fora de ordem, falha de fonte/síntese, retry e Nova análise; walkthrough final da matriz.
