# Checkpoint — Opportunities e Frontend B3 — 2026-10-07

## Escopo combinado

Opportunities deve verificar se existe uma oportunidade econômica sustentada por evidências atuais. A análise deve cruzar pesquisa datada de mercado, histórico de preço/volume, fundamentos disponíveis, curvas futuras PRE/DIC da B3 e exposição da carteira. Deve registrar contrapontos e fontes.

O agente classifica cada ativo como oportunidade qualificada, acompanhar, evidência insuficiente ou tese rejeitada. Apenas teses qualificadas podem receber prioridade positiva; se nenhuma passar pelo critério, o resultado correto é ranking vazio com explicação. Alvo institucional, volatilidade ou liquidez, isoladamente, não bastam para qualificar uma oportunidade.

A revisão completa é agendada uma vez por dia útil ao meio-dia de São Paulo. Uma execução longa é esperada. A tela deve acompanhar o estado, preservar o último relatório bom durante a atualização/falha e apresentar o relatório novo quando terminar.

## Implementação no branch

Branch `feature/react-functional-v43-integration`, PR #66 (draft). HEAD remoto confirmado nesta sessão: `0198434733ce7e45e156c64e80da8bcc3f0b627f`.

- O prompt de Opportunities pede cruzamento de notícias/eventos datados, histórico, fundamentos, curvas PRE/DIC e carteira; exige classificação por ativo e ordenação apenas de teses qualificadas, com fontes/contrapontos.
- O backend disponibiliza estado e último resultado da revisão, evita execuções duplicadas por lock e preserva a última execução concluída quando a atual falha.
- O frontend carrega o relatório salvo ao abrir, acompanha uma execução em andamento por polling e dá até 90 minutos à busca manual.
- O job diário usa o universo monitorado mais a carteira, pede pesquisa externa atualizada e inclui as curvas B3.
- O instalador cria um serviço systemd oneshot com limite de 90 minutos e timer de segunda a sexta às 12:00 em `America/Sao_Paulo`.

## Confirmação no Ubuntu em 2026-10-07

O usuário instalou o timer e verificou:

- `b3-opportunities-daily.timer`: `enabled` e `active (waiting)`.
- Próximo disparo informado pelo systemd: quinta-feira, 2026-10-08 às 12:00 (-03).
- `b3-opportunities-daily.service` ainda não executou; `journalctl` não tinha entradas. Isso é esperado antes do primeiro disparo.
- A desconexão SSH relatada ocorreu enquanto o usuário verificava o serviço; as evidências disponíveis não ligam essa desconexão ao timer.
- Não há confirmação nesta conversa do SHA atualmente checkoutado no servidor nem de reinício do processo HTTP `b3-runtime.service`. O timer estar ativo não comprova, por si só, que o frontend está usando as novas rotas de status/latest.

## Próximos passos para 2026-10-08

1. Confirmar no Ubuntu o SHA do checkout e que corresponde ao branch atualizado; verificar se `b3-runtime.service` precisa reiniciar para carregar as rotas novas de Opportunities.
2. Após a execução das 12h, validar `systemctl status b3-opportunities-daily.service`, journal, estado/resultados persistidos e cobertura/falhas do job.
3. Validar a resposta real do LLM por ativo: classificação, ranking vazio quando apropriado, evidências datadas e citações verificáveis.
4. Testar no frontend: duração longa com estado/progresso, refresh manual, preservação do relatório anterior, retorno à lista e abrir ABEV3 sem misturar a síntese de VALE3.
5. Retomar Market Intelligence: confirmar dados/notícias/eventos e as visualizações desejadas de fluxo estrangeiro e curva de juros; distinguir lacunas de backend/adaptador das lacunas de apresentação.
6. Consultar CI do último SHA. No momento deste checkpoint, o conector GitHub retornou nenhum status/check associado ao commit `0198434`; não tratar isso como CI verde.

## Limites do checkpoint

O timer foi confirmado ativo pelo usuário. A execução diária ainda não ocorreu e portanto não há resultado de produção, nem validação end-to-end da análise LLM agendada. O PR #66 permanece aberto e em draft. Nenhuma conclusão de oportunidade ou recomendação de investimento é inferida neste checkpoint.
