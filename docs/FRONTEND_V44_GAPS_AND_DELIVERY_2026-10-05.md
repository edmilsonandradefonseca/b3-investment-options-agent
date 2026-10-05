# Gaps e entregas V4.4 — 05/10/2026

Fonte normativa: FRONTEND_DECISION_WORKSPACES_SPEC_V1.2.md. Não redefine comportamento.
Baseline local: feature/react-functional-v43-integration, 5ccb458, limpo antes da documentação. PR #66 existente (draft, base fix/react-portfolio-api); main recebeu somente arquitetura em PR #68, 6372292. Nenhum AGENTS.md encontrado no checkout.

## Diagnóstico inicial por evidência

| Gap | IDs | Evidência / causa | Entrega |
|---|---|---|---|
| GAP-01 | LAB-01/02/06 | App.tsx run força analysis_mode=deterministic no Lab; pergunta natural fica no Copilot lateral. Deficiência de routing/UI confirmada, não inferência sobre capacidade do modelo. | E1: pergunta/continuação centrais, síntese sênior e LED, preservando contratos numéricos |
| GAP-02 | OPP-01–06 | App.tsx começa VALE3/RENT3/VIVT3/BBAS3, includePortfolioStocks=false; fluxo é screening manual; opportunity_screen.py tem teto20 e objetivos limitados. | E2: universo completo, orçamento de coleta, ciclo automático/manual, seleção material e detalhe |
| GAP-03 | WS-03, MI-03 | Classificador BRAPI trata nomes de crescimento/retorno/dívida como moeda por substring; unidade precisa de semântica explícita antes de exibir dinheiro. | E3: normalização, comparabilidade, fonte/freshness/quotas e regressão de dados→API→UI |
| GAP-04 | MI-01/02 | Panorama solicita determinístico; análise do ativo aparece depois de gráfico/indicadores. | E4: narrativa primeiro, panorama/setores e exposição |
| GAP-05 | WS-01 | Navegação inclui Overview, History e Risk além dos cinco workspaces aprovados. | E1: navegação principal corrigida, capacidades contextuais preservadas |
| GAP-06 | WS-06 | Yahoo é piloto; prioridade e franquia central V4.4 não comprovadas no runtime. | E3: adapter por capacidade + contador compartilhado e evidência de fallback |
| GAP-07 | WS-09 | CI 37250969015 aprovado no baseline; visual 37248585709 falhou na etapa de navegação (build passou). Ubuntu ativo/Windows precisam de verificação atual. | E0: diagnóstico do processo/API e telas; não equiparar checkout e processo |
| GAP-08 | LAB-03/04/05 | Cenários/economia existentes parciais; efeito completo multi-pernas exige casos reais. Não afirmar causa única para retorno histórico ausente. | E5: completar cálculo por família e visualização correspondente |

## Sequência de entregas completas

E0: contrato aprovado → inventário de versão/processo → APIs → navegador real. Diagnóstico sem reiniciar ou alterar carteira. Logs públicos somente metadados sanitizados.
E1: pergunta natural Lab → routing sênior/contexto → resposta central/continuação → LED → build, teste de contrato e runner visual. Não fecha multi-pernas.
E2: dados de ações/carteira/watchlist → revisão material backend → API de resultados/status → lista/detalhe Opportunities → abertura, refresh, zero oportunidades e falhas. Sem chain automática.
E3: Yahoo/capacidade → persistência/proveniência → OPLAB/BRAPI com orçamento → unidades/fundamentos → consumo nas três telas; validar concorrência e quota.
E4: dados macro/setor/ativo e exposição → síntese → panorama/ativo Market; targets separados do consenso e cadeia sob demanda.
E5: motores e contexto completos → comparações multi-pernas/antes-depois → gráficos/cenários → casos reais e Windows.

Cada entrega mantém teste, commit, run e status separados: implementado, verificado em fixture, verificado Ubuntu, aceito Windows. Sem preenchimento de PASS com base em hipótese.

## Runtime e aceite

Coleta atual pendente pelo workflow b3-v44-review. Resultados serão anexados por metadados, sem posições pessoais. Windows não é alcançado pelo runner Ubuntu; build preview não é a versão instalada Windows.

## Evidência atual e primeiro bloco

- Runner read-only 37310810098: PASS operacional. Checkout Ubuntu ac27ff3; serviço ativo PID2239, início 05/10 07:33 São Paulo. /version só informa 0.1.0, não SHA do processo: G01 continua parcial. /health LLM true; /analysis/live/PETR4 0,2s, 84 candles, último candle 02/10, zero contratos consultados. Não afirmar cotação intraday atual.
- Falha visual 37248585709: seletor de título antigo, comprovado contra AnalysisOutput.tsx. Corrigido o título esperado; não afrouxado gate de conteúdo.
- E1 iniciado: StrategySession central com pergunta livre, uma chamada sênior pela API existente, sem defaults dos formulários, histórico de perguntas/respostas e reset, LED e preservação de respostas em falha. Controles determinísticos existentes permanecem para compatibilidade; E1 ainda não fecha layout final/cálculos multi-pernas.
- Build local e check-decision-rendering PASS. Browser local bloqueado por download de Chromium truncado; validação de navegador segue no runner Ubuntu, onde Chromium existe. Fixture de navegador explicitamente distinta de aceite real.
- Publicação feita pelo conector GitHub porque git push HTTPS local não tem credencial. SHAs remotos são autoridade; commit local 1b3f17e não é SHA publicado.

## Validação após reinício manual — 05/10, 09:57 São Paulo

- CI 37312209716 e 37312843810: PASS nas revisões candidatas.
- Candidato ASGI 37312207143: pergunta natural com R$10 mil gerou duas alternativas canônicas em 2,4s; síntese sênior + tabela em 88,55s, tese291 caracteres/rationale1197. É evidência estrutural, não avaliação qualitativa completa.
- Navegador 37312005092: LAB-01/02/06 PASS com fixtures (pergunta central, ausência de defaults ocultos, continuação/reset). Teste global revelou seletores antigos e exigência de texto específico no prompt Market; corrigidos, suíte global novamente em execução.
- Entrega 37311815798: CI PASS e checkout avançado para d3624d1; sudo bloqueou restart. Usuário reiniciou manualmente. Auditoria 37312595988 confirma PID40014 e início09:51:37, checkout d3624d1 limpo, health ativo/LLMtrue. Não confundir a versão publicada posterior do React com a versão instalada Windows.
- API ativa após restart: pergunta natural resultou em stock_purchase_comparison com2 alternativas + síntese COMPLETED/PASS, sem erro, em68,06s. Histórico PETR4 respondeu em0,16s,85 registros, candle de05/10,zero cadeia. Data diária não comprova preço intraday executável.
- Primeiro bloco E1: campo central + LED + histórico; grafo conserva conversa como contexto histórico não autoritativo; interpretação exata de orçamento para exemplo aprovado. Layout com controles estruturados recolhidos e cinco itens principais publicado depois do checkout d3624d1; implantação Windows pendente.
- E2 Opportunities automática e material ainda NÃO implementada. E3 fontes/quotas/unidades, E4 Market completo e E5 multi-pernas continuam abertos. Não publicar aceite integral destas telas.

## Continuidade da validação — 05/10, após confirmação do usuário

- Revisão funcional React 34c794d: CI 37313923169 PASS. Build local da revisão aaa344e também PASS. Inclui narrativa completa antes das tabelas, indicador de processamento no topo, política de research escolhida pelo usuário e aviso quando a carteira muda após uma análise.
- Execução visual real 37313920068: contrato central LAB-01/02/06 passou com fixtures; navegação real passou por comparação, cenários e análise sênior de PETR4. A suíte completa NÃO passou: parou procurando o título antigo “Carteira canônica” no Copilot. O componente mostra “Carteira considerada”; a API havia retornado as posições. Correção de seletor em aaa344e, mantendo o gate de conteúdo e posições; novo aceite completo pendente.
- A execução anterior 37313146582 recebeu no fluxo PETR4 uma resposta sem result. Não equiparar essa ocorrência a um problema visual nem considerá-la resolvida só porque a execução seguinte passou. Diagnóstico sanitizado de status HTTP e tipo de erro foi acrescentado em c5b7041; acompanhar recorrência.
- A confirmação “feito” não comprova por si só uma instalação Windows. O processo Ubuntu comprovado permanece na revisão d3624d1 até nova evidência; preview do runner testa o React candidato contra essa API.
- Dependência de E2: implementar a política de fontes, proveniência e limite BRAPI de E3 antes de ativar coleta automática do universo B3 em produção. Trabalho de UI/contratos de E2 pode ocorrer antes; não ligar um refresh amplo no pipeline atual e chamá-lo de Opportunities concluído.

## E3 — primeiro bloco de fontes e unidades, 05/10

Implementado no candidato, sem equiparar à versão ativa:

- Histórico: arquivo local preservado; Yahoo → OPLAB → BRAPI para lacunas. Sobreposição OHLC Yahoo/local deve existir e divergir no máximo 0,5% antes de aceitar o complemento; incompatibilidade segue ao fallback. Isso verifica uma fronteira da série, não certifica todos os ajustes históricos.
- Cotação de ações: cache admissível primeiro; Yahoo → OPLAB → BRAPI. Timestamp Yahoo obrigatório, atraso potencial explícito e candle diário separado de cotação. Opções continuam no OPLAB. A política de cotação não certifica preço executável.
- Fundamentos: Yahoo/info primeiro; OPLAB declarado unsupported para essa capacidade no adapter atual; BRAPI complementa campos ausentes, sem sobrescrever o campo Yahoo já admitido. Cache por fonte/capacidade; fonte e datas acompanham cada métrica.
- Proventos assíncronos: Yahoo primeiro; BRAPI como fallback; projeção existente aceita snapshots Yahoo qualificados. Yahoo ex-date não vira data de pagamento e não inventa identificação de JCP; valores com pagamento desconhecido não compõem soma de proventos pagos.
- Quota BRAPI persistente SQLite, transação de reserva antes de cada tentativa/retry, compartilhada por API/jobs. /providers/budget/brapi expõe metadados locais, sem token nem posições.
- Unidades explícitas para dívida/patrimônio, crescimento, ROE e P/VP. O frontend diferencia percent, fraction e ratio, sem exibir moeda nestes campos. updatedAt não passa por data fiscal comprovada; CURRENT_SNAPSHOT aparece como período não verificado. O Lab exibe o snapshot e não calcula diferença fiscal entre períodos desconhecidos.

Configuração de produção: B3_BRAPI_LOCAL_ALLOWANCE é obrigatório para permitir chamadas BRAPI; default zero bloqueia HTTP. Configurar allowance conservador, B3_BRAPI_BILLING_TIMEZONE (default America/Sao_Paulo), B3_BRAPI_BILLING_DAY (1..28; default1), B3_BRAPI_OPERATIONAL_RESERVE (default100). B3_BRAPI_BASELINE_USED e B3_BRAPI_BASELINE_PERIOD registram consumo conhecido no período; contador local não prova saldo da conta. Teto absoluto local de15.000 menos baseline/reserva. B3_BRAPI_BUDGET_PATH permite apontar todos os clientes internos ao mesmo arquivo; default no data_dir compartilhado. Não presumir saldo inicial15.000 nem habilitar pedidos reais automaticamente.

Validação candidata no runner usa caches/quota temporários, arquivo histórico real em leitura e allowance zero. Não reinicia systemd, não escreve carteira e não gasta BRAPI. Conclusão real depende do resultado do workflow b3-v44-sources.

Continuam abertos: demonstrações completas Yahoo, consenso/alvos/estimativas/revisões/notícias, calendário de pregão, reconciliação com saldo externo BRAPI, alertas visuais de quota, dossiês Qwen/refresh por evento e universos amplos. E3 não está integralmente fechado só pelo adapter de info/histórico/proventos. E2 automático aguarda esses dados e critérios materiais; E4/E5 permanecem pendentes.

## Aceite real do primeiro bloco E3 — 05/10, 11h15 São Paulo

Workflow37321575947 PASS no candidato485e521, ambiente Python isolado, sem restart nem gasto BRAPI:

| Ativo | Histórico | Fontes da série | Fundamentos | Fonte dos fundamentos | Latência histórico / fundamentos |
|---|---:|---|---:|---|---|
| PETR4 | 85 | COTAHIST + Yahoo | 33 | Yahoo | 1,15s /0,80s |
| ITUB4 | 85 | COTAHIST + Yahoo | 27 | Yahoo | 0,30s /0,82s |
| BBDC4 | 85 | COTAHIST + Yahoo | 27 | Yahoo | 0,31s /0,82s |

Cotação Yahoo: leitura0,51s; timestamp14:00:45UTC observado na coleta14:15UTC, flags potentially_delayed/not_executable_quote. Não é cotação imediata garantida. Para ITUB4/BBDC4, campos core ausentes levaram à etapa BRAPI, bloqueada por allowance zero; métricas Yahoo admissíveis permaneceram disponíveis e diagnósticos registraram a limitação. Zero tentativas HTTP BRAPI.

CI remoto485e521,bd80a78,296efa9 PASS; testes locais ampliados para952, build/checagem de renderização PASS. Revisões posteriores precisam de seus próprios gates. Cache tem um envelope por capacidade/fonte/ticker para não acumular arquivos de janelas diárias indefinidamente.

Corrigido outro gap de consumo: Mercado exibia texto fixo BRAPI independentemente da origem. Agora fonte aparece por métrica e datas fiscal/observada/disponível são separadas; análise B3 vem antes de cards e gráficos. É primeiro bloco de MI-02/03, não panorama Market completo.

A série projetada para gráficos e retornos mantém uma única base: se um trecho local não tem adjusted_close, não anexar fechamento ajustado Yahoo ao fechamento bruto do arquivo. O cache Yahoo preserva adjusted_close; a projeção de série usa close com flag explícita quando necessário. Não representa retorno total nem valida todos os eventos/splits históricos.

Workflow legado37321575811: economia candidata PASS; checkout produção avançou d3624d1→485e521; sudo recusou restart. Depois falhou no teste congelado em02/10, embora a API retornasse candle05/10. Corrigidos gate dinâmico de freshness/proveniência e separação entre teste automático e ativação. Push valida; alteração de checkout/restart fica no workflow_dispatch de ambiente preparado, com preflight de dependência/privégio. Processo ativo não comprovado como485e521; não tratar checkout atualizado como deploy. Windows segue não verificado.

## Correções adicionais de cobertura e semântica monetária

- Market /analysis/live solicitava apenas120 dias mesmo quando o gráfico pedia1 ano. O endpoint passa a solicitar395 dias e informa requested_history_days; falta de cobertura real continua explícita. Não prometer histórico completo de IPOs ou períodos que as fontes não conseguem qualificar.
- Histórico Yahoo exige symbol e BRL nos metadados; identidade ausente não é inferida como validada.
- VALE3 e outros emissores podem ter cotação BRL e demonstrações USD. O adapter passa a admitir razões sem moeda e montantes financeiros na moeda declarada, distinguindo marketCap na moeda da cotação. Não converter FX implicitamente nem atribuir moeda aos dados por ação/enterpriseValue com origem ambígua entre moedas; esses campos ficam para fallback qualificado.
- forwardPE/forwardEps recebem flags de estimativa agregada e horizonte não verificado; não representam lucro realizado nem relatório individual. O teste real é ampliado paraVALE3. CI e runner deste incremento precisam ser conferidos antes de ativação.


## Evidência ampliada de fontes — candidato 2b5d9a8

Runner37328946904 PASS; CI37328957768 PASS. Os 40 testes direcionados passaram no ambiente isolado com yfinance1.7.0. Leitura real via APIs candidatas:

| Ativo | Pontos de histórico | Fundamentos | Latência histórico / fundamentos |
|---|---:|---:|---|
| PETR4 | 270 | 33 | 0,63s /0,80s |
| ITUB4 | 270 | 27 | 0,34s /0,80s |
| BBDC4 | 270 | 27 | 0,63s /1,10s |
| VALE3 | 270 | 33 | 0,31s /1,03s |

Séries COTAHIST + Yahoo, fundamentos Yahoo. VALE3 retornou moeda BRL neste snapshot: o caso real comprova disponibilidade; a segregação de moedas USD/BRL foi verificada em teste controlado, não por esse snapshot. Cotação PETR4 observada14:43:43UTC, coleta14:58:43UTC, potencialmente atrasada e não executável. Zero tentativas HTTP BRAPI; quota local bloqueada. Serviço systemd não foi alterado.

Runner37328946825: ingestão de relatórios e validações assíncronas PASS; Qwen drenou4 lotes/4 itens, todos READY, sem falhas, em111,77s. O gate de gráfico falhou porque seu critério ainda limitava a120 dias, enquanto a API entregava corretamente270 sessões na janela395. Não foi falha de ingestão nem de renderização. Correção6d1ecdb valida requested_history_days=395 e deriva dessa janela os limites, mantendo checks de persistência, duplicidade, freshness, timestamps e ausência de cadeia. CI37329813396 e runner37329795381 disparados; conclusão pendente ao registrar este checkpoint.

Aceite visual37324999672 PASS para frontend d79ab6c; alterações2b5d9a8/6d1ecdb não mudam esse frontend. Processo Ubuntu e instalação Windows continuam exigindo confirmação de versão ativa. Dependência yfinance precisa estar instalada no ambiente de produção antes da ativação; restart requer autenticação sudo interativa já observada. E2 Opportunities automática, E4 panorama completo e E5 multi-pernas não são considerados concluídos por estes resultados.


## Correção dos gates e conclusão — candidato 0c9d7c8

CI37331054232 PASS; workflow Ubuntu37331045904 PASS completo.

- 6d1ecdb: critério do gráfico deriva de requested_history_days=395, mantendo mínimos, cobertura persistida, duplicidade, freshness e disponibilidade.
- 44ba979: falha no Qwen não impede o diagnóstico independente dos contratos API, mas continua reprovando o workflow. Flags públicas identificam a categoria do adiamento sem imprimir conteúdo/erro sensível.
- Runner37330254041 identificou LOCAL_REASONING_BUSY em duas tentativas: três itens READY, um restante. O bloqueio compartilhado foi respeitado; não houve falha terminal do modelo. A exigência anterior de exatamente quatro batches/tentativas desconsiderava o adiamento previsto no contrato da fila.
- 0c9d7c8: validação espera requests elegíveis após o backoff persistido, por até360 segundos, mantendo lock e schedule de produção. Exige quatro IDs distintos READY, fila vazia, zero FAILED/DEGRADED. Adiamentos intermediários não equivalem a falha quando há conclusão. Este resultado não valida todos os caminhos possíveis de retentativa.
- Nova execução: quatro lotes/quatro itens READY, nenhum adiamento ou erro, fila vazia,106,71s. A contenda anterior permanece registrada; sucesso posterior não comprova ausência de contenda futura.
- API candidata PETR4:270 pontos e contrato PASS em0,23s, usando COTAHIST + OPLAB neste ambiente de dependências do runtime. Distinta da validação Yahoo no ambiente isolado37328946904.
- Contratos Opportunities/Strategy Lab e comparação natural explícita PASS. Opportunities manteve20 candidatos e DEFERRED_INCOMPLETE_CONTEXT: não é prova de busca material automática ou cobertura de todaB3.
- Screening existente: ranking de volatilidade com universo parcial e diferenças de janela explicitadas; fundamentos indisponíveis neste ambiente. Não declarar resolvida essa cobertura só porque o gate estrutural passa. Duas sínteses sênior retornaram HTTP200 e duas avaliações por alternativa,102,68s e112,61s. Evidência estrutural/econômica, sem aceite qualitativo integral.
- Verificações HTTP do serviço ativo passaram, mas PETR4 continua85 pontos, sem requested_history_days. Checkout produção485e521; PID51544, início05/10 às10:05:22 SãoPaulo. O processo iniciou antes da atualização anterior de checkout; não inferir SHA carregado a partir desse checkout. Ativação foi SKIPPED neste push. A dependência Yahoo e o restart devem acompanhar a atualização antes de concluir deploy.
- Windows segue não verificado. E2 automático/universo completo, E4 panorama/fontes completas e E5 multi-pernas continuam abertos. Próximo passo operacional: atualizar produção para o candidato validado, preparar dependências e reiniciar com autenticação sudo; confirmar API de395 dias e fontes depois. Próxima entrega funcional: E2 com seleção material e ciclo automático/manual, sem pesquisa automática de cadeias.


## Retomada do checkpoint — OPP-01/OPP-02 UI de atualização, 05/10/2026

Fonte normativa: `main/docs/ARCHITECTURE_V4.4.md` e `main/docs/FRONTEND_DECISION_WORKSPACES_SPEC_V1.2.md`. A V1.2 mantém a busca de ações explícita, sem varrer chains; este incremento implementa o fluxo manual e a apresentação do estado, sem declarar concluída a descoberta automática/material.

- Commit GitHub `045a34db8c460ceaddc9bc9047873712b468fbfa`: Opportunities ganhou CTA único “Buscar novas oportunidades”, estado neutro/amarelo/verde/vermelho, início/término, fontes, trava contra duplo envio e preservação da análise anterior enquanto uma atualização está em andamento ou falha. O pedido continua usando o screening determinístico existente seguido da síntese disponível; ranking observado não vira score geral ou recomendação de compra.
- O primeiro aceite visual `37342748354` comprovou no runner Ubuntu o caso normal e um 503 controlado: tabela anterior permaneceu visível e LED ficou vermelho. A caminhada depois parou numa asserção de Histórico ambígua (quatro linhas com o mesmo rótulo), não em Opportunities.
- Commit `d51c793b02e12de406b1e547fc31bafd34ab4b54` ajustou o seletor para exigir presença de um resultado repetido sem exigir unicidade. CI `37343614434` PASS; caminhada visual real `37343607577` PASS em todas as etapas após o ajuste, contra API Ubuntu e fixtures/visuais configurados pelo workflow.
- Verificação local do commit de UI: `npm ci`, `npm run build`, `node scripts/check-decision-rendering.mjs`, `node --check scripts/validate-cockpit-real.mjs` e `git diff --check` PASS. Pytest local não estava instalado; o job de testes Python do CI passou.

### Estado restante — não coberto por estes commits

- OPP-01 automático na abertura/snapshot ainda MISSING; não há deduplicação de revisão/sessão ligada ao snapshot.
- OPP-04 materialidade e cobertura completa da carteira/universo continuam PARTIAL. Screening manual segue teto explícito de 20 ativos e objetivos observados de volatilidade/liquidez; não há varredura geral B3, seleção material de tese ou processamento em lotes validado para carteiras maiores. O checkbox de carteira não substitui esse aceite.
- O LED cobre o refresh manual; não representa job automático, scheduler ou última análise persistida após reiniciar a aplicação.
- O frontend candidate passou no runner, mas não foi instalado no Windows. A API Ubuntu ativa continua em estado separado do checkout; esta entrega não reiniciou nem alterou `b3-runtime.service`.

Próximo bloco conforme sequência aprovada: desenhar/implementar OPP-01 e OPP-04 completos sobre o contrato backend, incluindo snapshot vigente e universo com lotes/coorte global sem truncamento, materialidade determinística/sênior, status consultável e atualização manual idempotente. Não ativar busca ampla até demonstrar orçamento/latência e cobertura no runner.


## Implementação em curso — OPP-02/OPP-06: escopo íntegro de carteira, 05/10/2026

Este registro atualiza o diagnóstico antigo acima, que descrevia o checkbox e teto de 20 ativos observados antes desta revisão. Fonte funcional normativa permanece `FRONTEND_DECISION_WORKSPACES_SPEC_V1.2.md`; opções em Opportunities são apenas contexto e não acionam chain.

- O frontend removeu o opt-in de carteira: toda busca manual envia `include_portfolio_stocks=true`, mantém os candidatos acompanhados e explica que opções abertas são contexto.
- `StockOpportunityScreenService` une candidatos com todos os tickers de ações do snapshot vigente, sem truncamento de 20, e consulta ativos com até quatro trabalhadores concorrentes. Ordem de apresentação permanece estável. Erro por ativo é localizado; falha de snapshot não apaga a análise dos candidatos e sinaliza `CURRENT_PORTFOLIO_UNAVAILABLE`.
- Opções do snapshot entram como contexto em cada ativo-objeto. Underlyings existentes somente em opções também são consultados para compor a exposição, recebem `OPTION_UNDERLYING_CONTEXT` e são excluídos do ranking de descoberta. O fluxo não solicita cadeias.
- Detalhe exibe quantidade de ações, opções abertas, obrigação de PUT vendida com strike/multiplicador observados e cobertura de CALL vendida. Termos ausentes não são convertidos em zero; não há multiplicador fixo presumido.
- IDs rastreados: `OPP-02` PARTIAL (lista/detalhe com exposição; decisão material, seleção persistida e apresentação do agente ainda faltam); `OPP-04` PARTIAL (universo de ações observado sem truncamento de carteira, mas sem seleção material/coorte ampla); `OPP-06` PARTIAL (contexto de posições e ausência de chain cobertos estruturalmente; aceite com carteira real pendente). `OPP-01` segue MISSING. O status amarelo/verde/vermelho é somente refresh manual existente.
- Testes adicionados para união de 23 ativos sem teto, snapshot ausente com continuidade e exposição de PUT/CALL incluindo ativo-objeto somente de opção. Validação backend/frontend ainda precisa rodar neste candidato; não declarar aceite do runner/produção.

Próximos gates: validar build e suíte de domínio; resolver/diagnosticar o teste HTTP que pendura no Python local; rodar CI em Python suportado; executar cenário do runner com snapshot vigente sanitizado; então revisar custo/latência e fechar uma seleção material versionada antes de implementar análise automática OPP-01.


## Resultado do candidato publicado — OPP-02/OPP-06 parcial, 05/10/2026

- Branch `feature/react-functional-v43-integration`, checkpoint publicado antes deste registro: `840a0f769f40c8963d454fb305b825aaf4b17078`; PR #66 permanece aberto em draft.
- CI `37361024443` para `840a0f7`: PASS — suíte Python completa em Python 3.14, build React, `check-decision-rendering` e testes de apresentação. O erro intermediário `37361015148` em `d4d7657` ocorreu antes da atualização correspondente do teste antigo de limite de 20; a revisão final substituiu a expectativa obsoleta, e CI integral subsequente passou.
- Local: 13 testes direcionados de Opportunities e compilação Python PASS; `npm run build`, `check-decision-rendering` e sintaxe da validação do navegador PASS. O teste de rota com `TestClient` pendurou no Python 3.12 local; CI Python 3.14 executou a suíte inteira com sucesso.
- Workflows Ubuntu: a comparação real `37361012415` está associada à revisão intermediária `d4d7657`; a caminhada visual mais recente observada (`37361007180`) ainda testa revisão intermediária `9a168d5`. Ainda não há PASS de browser ou API de produção para `840a0f7`.
- Nenhum checkout, processo `b3-runtime.service`, carteira ou instalação Windows foi alterado por esta entrega. Ativação de produção não realizada. Os dados reais do snapshot BTG ainda precisam ser exercitados pelo runner para aceitar OPP-06.

### Situação atual de requisitos

- `OPP-02` PARTIAL — união completa estável e sem teto, detalhe de exposição exibido; composição material, agente primeiro e persistência de item selecionado permanecem.
- `OPP-04` PARTIAL — processo não trunca carteira/candidatos, mas o screening de volatilidade/liquidez não é descoberta material e nenhuma varredura geral da B3 foi prometida.
- `OPP-06` PARTIAL — contratos abertos e cobertura são contexto determinístico sem chain; validação real BTG e revisão do impacto agregado aguardam runner.
- `OPP-01` MISSING — análise automática idempotente por snapshot/sessão não está implementada. Não ativar até orçamento/latência e idempotência backend estarem demonstrados.
- Strategy Lab e Market Intelligence não foram modificados neste incremento. LAB-01/02/06 continuam com evidência prévia; demais LAB, MI-01 panorama completo e MI-04/05 cobertura de research continuam parciais/conforme matriz anterior.

Próximo: concluir aceite Ubuntu do candidato com CI verde e snapshot sem conteúdo pessoal em artifact; depois implementar e testar OPP-01/OPP-04 versionados. Em paralelo seguir E4 (panorama MI) e E5 (multi-pernas Lab).

## Retomada operacional — CI/Ubuntu, 05/10/2026 (UTC)

- Branch: `feature/react-functional-v43-integration`; HEAD no início deste registro: `0aefb509357d651fd6fbd6d02c549a91871c86f3`. PR #66 segue aberto, draft, base `fix/react-portfolio-api`.
- Commit `fdb82c7`: CI `37364697510` PASS (Python, build React, apresentação); visual `37364691637` PASS em 1920/1440/1366, sem erros de página. No mesmo percurso, Opportunities recebeu HTTP 400 da API ativa, JSON com apenas `detail` textual. A UI isolada foi verificada com fixture explicitamente sem preço/carteira/recomendação; não é aceite real do endpoint.
- Commits `fdb82c7`, `9fcaa15` e `88beb13` tornam o diagnóstico do 400 limitado e sanitizado: campos estruturais permitidos, ticker/valores/e-mail/caminhos mascarados, prévia curta. O teste atualizado aguarda vaga do runner visual; ainda não há mensagem diagnóstica confirmada.
- Runner `37363177645` (revisão `3f1bb52`) parou no gate porque aguardou o CI por 6 minutos; etapas de dados/deploy foram puladas. Não foi falha dos testes Python nem restart.
- `5ab4c4d` aumentou o timeout de espera do gate para 15 minutos e o limite do job para 60; CI `37364883777` ainda estava enfileirado quando consultado. Para não ocupar o self-hosted durante essa fila, `0aefb50` separou `wait-for-ci` em job GitHub-hosted e deixa o Ubuntu self-hosted iniciar só depois do gate verde. Sintaxe YAML foi validada localmente. Execuções `37365880060` (CI) e `37365875125` (Ubuntu candidate) estavam enfileiradas, sem validação de dados ainda.
- O step de atualização/restart do serviço continua condicionado a `workflow_dispatch`; os eventos `push` aqui não reiniciam produção. Nenhum restart, carteira ou instalação Windows foi alterado nesta retomada.
- Requisitos: `OPP-02/06` PARTIAL (união sem teto/exposição codificadas, API ativa não aceita a tela neste teste); `OPP-01` MISSING e `OPP-04` PARTIAL (revisão automática idempotente/materialidade ainda não implementadas). Strategy Lab e Market Intelligence seguem PARTIAL conforme a matriz acima; aceite de dados atuais no runner aguarda workflow.
- Próximo: obter a prévia sanitizada do 400; corrigir o contrato no componente correto; executar candidato Ubuntu após CI; revalidar Opportunities com snapshot real; atualizar esta seção com os resultados, sem promover fixture a aceite. Estratégia `ITUB4 × BBDC4` e ativo `PETR4` precisam passar no mesmo candidato real. Sem reinício manual, não afirmar ativação do processo.

## Checkpoint atualizado — 05/10/2026 (CI e aceite real do Strategy Lab)

- Branch: `feature/react-functional-v43-integration`. SHA testado no runner Ubuntu: `9bcff39a0266e0d16910d92c2244fc32a73baaed`; o workflow registrou esse SHA no log como `CANDIDATE_SHA`.
- CI `37366601794` terminou com os dois jobs aprovados: Python `test` e React `frontend-build`, incluindo a verificação de que a informação de decisão chega ao frontend. A primeira falha era indisponibilidade temporária de alocação do runner hospedado; não era falha do código nem os avisos de depreciação.
- Corrida antiga `37365880060` para `0aefb50` continua sem gate completo: `frontend-build` passou e `test` foi cancelado. CI para `f8052ba` (`37370830005`) segue aguardando runners; em `9bcff39` (`37371120889`), frontend passou e Python ainda aguarda. O gate determinístico precisa de CI verde para o mesmo SHA.
- Aceite real no Ubuntu `37371112897` PASSOU em cerca de 1m12s, com a síntese sênior em 60,22s. O runner importou o código candidato como ASGI contra os dados/serviços locais, sem reiniciar `b3-runtime.service`.
- `LAB-01`: pergunta natural com orçamento de R$ 10.000 comparando compra de ITUB4 e BBDC4; resposta determinística retornou ambas as linhas de comparação, sem erro.
- `LAB-02`: mesma tese em modo `stored_first`; a comparação canônica trouxe duas ações e a síntese sênior produziu tese (230 caracteres) e justificativa (927 caracteres), sem erro.
- O Neo4j emitiu avisos de propriedade `valid_to` ausente em parte do grafo. Não impediram o aceite, mas devem ser avaliados como qualidade/esquema de dados; não declarar cobertura temporal validada por este teste.
- Este aceite é do backend candidato, não do processo HTTP ativo. O serviço de produção não foi reiniciado, e a carteira nem o ambiente Windows foram alterados.
- Opportunities continua PARTIAL: o endpoint ativo ainda devolveu HTTP 400 por exceder o limite legado de ativos. O candidato remove esse teto, mas falta validar a chamada com a carteira real no processo ativo. O fallback visual não é aceite financeiro.
- Market Intelligence permanece PARTIAL: os fluxos HTTP e a tela foram exercitados em validação visual anterior, mas a cobertura integral atual de gráfico 1s/1m/1a, notícias/eventos, targets e síntese explicada ainda não foi confirmada end-to-end neste checkpoint.
- PR #66 continua aberto como draft. Nenhuma ativação do serviço foi feita. A etapa de restart permanece condicionada ao workflow manual e à disponibilidade de `sudo -n systemctl restart b3-runtime.service`.

### Próximos passos rastreáveis

1. Aguardar CI Python verde no SHA candidato atual e deixar o workflow `b3-workspace-deterministic.yml` passar pelo gate; então conferir o log `CI_GATE_RUN` para comprovar SHA e conclusão exatos.
2. Usar os resultados do Ubuntu para fechar a comparação ITUB4 × BBDC4; validar ainda PETR4 em Market Intelligence e corrigir o 400 de Opportunities no limite apropriado (fonte/união de símbolos → API ativa), sem tratar fixtures como dados reais.
3. Executar aceite de carteira/posições/opções real no processo ativo; ativar por workflow apenas quando as verificações prévias passarem. Se `sudo -n` continuar bloqueado, registrar a ativação como BLOCKED e manter o serviço atual.
4. Atualizar esta matriz e o PR #66 com os resultados de cada endpoint e tela. O aceite atual não conclui UC01–UC12, não certifica cobertura financeira total e não conclui as três áreas end-to-end.


## OPP-01/04 materialidade versionada e integração visual — 05/10/2026

- Código no branch `feature/react-functional-v43-integration`, revisão funcional `f4ef6ca465de6f1cf041903b9defc167196da5b3` (documentação deste checkpoint será o commit seguinte); PR #66 segue aberto e draft.
- OPP-01: busca automática de snapshot e busca manual compartilham trava/chave e preservam o resultado anterior em falha. A validação de navegador para duplicação por navegação está no run `37381273145`; esse run e o novo aceite visual `37382495089` precisam terminar antes do aceite da implementação mais recente.
- OPP-04: criado `B3_STOCK_MATERIALITY_TARGET_REVIEW_V1`. Só cria item de revisão com cotação admissível de até 7 dias e alvo primário já qualificado que implique potencial condicional de preço >=15%. Isso não vira retorno esperado, probabilidade, BUY ou ranking de compra. Outros ativos ficam em “acompanhar”; consulta de alvo/cotação falha resulta em “evidência incompleta”. A lista não preenche quota.
- OPP-02/03/05/07: frontend mostra candidatos de revisão separados do acompanhamento, exibe alvo/fonte, risco observado e exposição de carteira, e distingue status ausente, cobertura incompleta e nenhum alvo que atingiu esse critério. Um scan vazio nesse critério não afirma ausência geral de catalisadores. A síntese sênior continua necessária para uma conclusão geral do universo e cobertura de eventos.
- Testes novos: item >=15% entra em revisão; item abaixo do limiar vai para acompanhamento; falha da fonte não se torna ausência. CI `37382502585` PASS (suíte Python, build React e decisão renderizada).
- Validação real: workflow determinístico candidato anterior `37380501773` PASS, incluindo triagem com snapshot real e PUT/ações abertas somente como exposição; o run atual para materialidade `37382349821` aguarda o runner Ubuntu. A etapa de reiniciar processo ativo foi SKIPPED; não afirmar implantação ativa.
- Status rastreável: OPP-01 PARTIAL até aceite de navegador em revisão atual; OPP-02 PARTIAL (lista/detalhe/exposição, seleção persistida e detalhe qualitativo a validar); OPP-03 PARTIAL (síntese sênior e cobertura por ativo ainda precisam aceite completo); OPP-04 PARTIAL (regra versionada implementada, validação com carteira/targets reais e revisão da política pendentes); OPP-05 PARTIAL (estado backend distinto, mas conclusão válida exige síntese sênior); OPP-06 PARTIAL (posições BTG reais foram reconciliadas, mas posição(s) com identidade inválida ficam expressamente sem associação); OPP-07 PARTIAL (filas separadas, visual runner pendente).
- Causa remanescente de latência até ~210s: o enriquecimento de pesquisa da síntese por ativo ainda pode buscar notícias serialmente para muitos tickers. O limite explícito de 20 tickers em `WorkspaceIntelligenceContextService` também precisa de um contrato de enriquecimento orçado sem truncar o universo determinístico. Próxima correção é delimitar esse fan-out e testar carteira >20 sem afetar cobertura do screening.
- Próximos gates: (1) aceite de browser `37382495089`; (2) run Ubuntu `37382349821`; (3) medir latência total da abertura/manual com cobertura e síntese; (4) cobrir/enriquecer notícias nos ativos priorizados e testar vazio válido vs falha parcial/total; (5) atualizar essa matriz com evidências antes de declarar OPP-01–07 concluídos. HEAD informado pelo PR #66 após a atualização deste registro.


## Retomada Opportunities — cobertura orçada e validação no runner, 05/10/2026

- HEAD validado: `70de1d92034ed2f7b29545a10831fd1cd6bc0bbc`, branch `feature/react-functional-v43-integration`; PR #66 segue aberto/draft.
- Correções publicadas: limite de enriquecimento síncrono em até 8 ativos prioritários, sem truncar screening determinístico nem exposição da carteira; UI informa quantos ativos receberam contexto complementar e quais seguem apenas com evidência determinística. O orçamento tolera `requested_universe=None` sem interromper a análise parcial.
- O workflow determinístico passou a disparar quando o módulo de materialidade, serviço de Opportunities e respectivos testes mudam. Isso fecha uma lacuna de validação que deixava módulos recém-adicionados fora do runner.
- CI `37383865623`: PASS — testes Python, build React e verificação de apresentação no SHA acima.
- Aceite visual `37383566507`: PASS; percorreu o cockpit no runner Ubuntu sem erros. O código React deste run é o mesmo mantido no SHA validado; os commits posteriores alteraram apenas materialidade/testes/workflow.
- Aceite determinístico Ubuntu `37383862634`: PASS no SHA exato. Discovery e fila Qwen passaram (112,4s para drenagem observada), contratos do workspace passaram, comparação sênior passou e o endpoint PETR4 devolveu série/fonte válidas sem solicitar cadeia. A etapa de atualizar/reiniciar `b3-runtime.service` foi SKIPPED; portanto, isso comprova o candidato via ASGI e a API já ativa separadamente, não ativação do serviço.
- Screening Opportunities com a carteira real incluiu a união de ações e opções sem perder subjacentes; validação de carteira real passou. A resposta observada da tela foi parcial/incomparável (`DEFERRED_INCOMPLETE_CONTEXT`) e o teste de orquestração não pediu síntese (`NOT_REQUESTED`). A análise sênior de oportunidades executada em chamada focada passou, mas levou 94,5s; esse resultado isolado não prova que a tela Opportunities entregue a conclusão integrada em uma busca.
- Latências observadas: endpoint Opportunities candidato no teste progressivo ~1,43s; triagem candidata com carteira ~4,15s; chamada sênior de oportunidades ~94,5s. Não somar tempos de rotas separadas como se fossem uma busca de UI.
- Estado rastreável: OPP-01 PARTIAL (revisão automática/idempotência e visual passaram em revisões anteriores, mas resposta integrada não concluída); OPP-02 PARTIAL (posição/exposição e detalhes reais passam estruturalmente; conclusão econômica integrada continua pendente); OPP-03 PARTIAL (fonte/cobertura/Qwen têm evidência, mas a síntese não é solicitada/entregue no percurso Opportunities validado); OPP-04 PARTIAL (materialidade versionada e orçamento preservam universo, porém ranking de descoberta real continua incomparável quando falta contexto); OPP-05 PARTIAL (sem evidência visual de decisão final para a carteira real); OPP-06 PARTIAL (união/exposição real passa, mas identidades sem ticker continuam sem associação); OPP-07 PARTIAL (estados de atualização preservados, mas conclusão íntegra não foi demonstrada na tela com dados reais).
- Próximo bloqueio end-to-end: rastrear o `DEFERRED_INCOMPLETE_CONTEXT` do fluxo real até as evidências específicas ausentes; conectar síntese sênior assíncrona à resposta persistida que a UI consome, sem bloquear a triagem nem inventar dados. Depois repetir uma única busca completa pela UI e medir tempo total. Não reiniciar produção neste push.
