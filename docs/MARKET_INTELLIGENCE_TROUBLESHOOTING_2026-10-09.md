# Market Intelligence — troubleshooting 09/10/2026

## Estado confirmado
Correção de código instalada; ativação HTTP pendente de reinício autenticado.
Branch: feature/react-functional-v43-integration; PR #66 continua draft.
Revisão do workflow de diagnóstico: 979186635e0d8e30be579b84e8b67eba917de411.

## Causas e alterações
- Curva TaxaSwap: B3 retornou HTTP 200 com ZIP externo vazio para data ainda não publicada. O pyettj levantava ParsingError e o adaptador abortava. O adaptador agora reconhece somente ZIP válido vazio como NO_DATA e busca a data anterior, dentro do limite existente de oito dias. Arquivos malformados continuam falhando; TLS verificado preservado.
- Frontend: erro de consulta não é ausência de observações. Os estados vazios deixam de aparecer junto ao erro; preservação de dados anteriores só é anunciada quando há dados carregados.
- Fluxo estrangeiro: DADOSDE_MERCADO_API_TOKEN ausente no processo ativo e nos arquivos verificados. Não existe credencial para habilitar essa fonte nesta sessão; não fabricar dados nem substituir fonte silenciosamente.
- Instalador editable da venv foi vinculado ao checkout canônico /opt/b3-investment-options-agent (sem atualização de dependências), com caminho de importação verificado. Isso não atualiza módulos que já estão carregados no processo ativo.

## Evidências
- Quatro testes focados do adaptador passaram localmente e no runner Ubuntu.
- Build React local e build/renderização do workflow visual passaram.
- Adaptador corrigido no runner retornou 283 vértices PRE, tanto no processo de diagnóstico quanto em thread.
- Windows installer build: https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37937322132 — SUCCESS, revisão 12a2ed8.
- Diagnóstico final: https://github.com/edmilsonandradefonseca/b3-investment-options-agent/actions/runs/37938921930 — FAILED por ativação não comprovada. Esse resultado é intencional: o gate exige API ativa e processo iniciado depois da instalação.
- systemctl --no-ask-password restart recusou a operação: autenticação interativa necessária.
- MainPID 2311 e listener API PID 2348 continuaram ativos; início do serviço 09/10 às 08h55 BRT, anterior à instalação. A API continuou retornando 503. Não declarar correção ativa.
- sudo -n reportou sucesso sem mudança comprovada do processo; esse retorno isolado não conta como reinício.
- CI ampla continua com a falha preexistente tests/test_v42_pilot_auditor.py (LIMITED versus PASS_WITH_COVERAGE_GAPS). Não há CI ampla verde.

## Instalação e limite
O deploy foi somente do arquivo src/b3_agent/providers/b3_yield_curve.py, após confirmar checkout sem alterações rastreadas. Não avançou o HEAD do checkout de produção; o provider instalado constitui uma modificação local rastreada. Uma integração posterior deve reconciliar essa alteração antes de aplicar o gate de checkout limpo; não sobrescrever outras alterações.
O frontend desktop do usuário não foi atualizado automaticamente. O instalador acima contém as mensagens corrigidas.

## Próxima ação
No terminal Ubuntu, executar sudo systemctl restart b3-runtime.service com autenticação local.
Depois validar GET /market-intelligence/yield-curves?curve=PRE: HTTP 200, status OK, as_of real e observações não vazias. Confirmar /health e processo posterior à instalação.
Para fluxo, configurar credencial válida DADOSDE_MERCADO_API_TOKEN em arquivo de ambiente carregado pelo serviço, sem enviar seu valor em chat/logs, reiniciar e validar /market-intelligence/investor-flows.
Não marcar Market Intelligence completo enquanto esses aceites estiverem pendentes.
