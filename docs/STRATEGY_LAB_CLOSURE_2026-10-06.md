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

CI 37490393724 passou com 1.019 testes Python, build React e renderização. Walkthrough 37490385165 passou na fixture de rolagem e no cockpit real em 1920/1440/1366. Ainda falta o aceite OPLAB no processo ativo: gate 37487319451 confirmou hash divergente e encerrou sem testar o novo código. A revisão não foi instalada nem reiniciada; aguardamos autorização conforme a preferência do usuário antes dessa ativação.

Este incremento não fecha o Lab: reconciliação de caixa, obrigações e cobertura completas; cenários com horizonte/choque explícitos; e aceites reais dos outros casos da matriz permanecem abertos. Caixa líquido após operação exige custos conhecidos; lucro acumulado requer histórico; vencimentos distintos não recebem ranking ou payoff comum. Nenhuma ordem é enviada.
