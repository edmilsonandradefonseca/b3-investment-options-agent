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
