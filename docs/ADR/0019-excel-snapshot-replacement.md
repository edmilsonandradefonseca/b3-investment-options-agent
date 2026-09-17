# ADR-0019 — Excel como snapshot substitutivo do estado atual

## Status
Accepted

## Contexto
O dashboard precisa representar o estado atual da carteira e das informações de opções a partir dos arquivos Excel fornecidos pelo usuário.

Uma entrada manual de BUY/SELL no dashboard pode divergir do extrato/posição oficial e criar dois estados concorrentes.

## Decisão
O dashboard não oferece mais **Registrar operação**.

A carga de dados será feita por dois snapshots independentes:
1. **Excel de Ações / Portfolio**
2. **Excel de Opções / Transações**

Cada carga é **substitutiva, não acumulativa**.

Quando um novo arquivo é carregado:
- o arquivo é validado antes de substituir o snapshot ativo;
- o snapshot anterior daquele domínio deixa de ser o estado corrente;
- nenhuma linha é adicionada ao snapshot anterior;
- dados de cargas anteriores não são somados ao novo arquivo;
- se a validação falhar, o snapshot anterior permanece intacto.

## Princípio
> **Excel carregado = snapshot atual daquele domínio.**

Isso é diferente de conhecimento histórico e de decisões persistentes. Histórico de decisões, evidências e memória continuam sujeitos às respectivas políticas de lifecycle.

## Contrato operacional

Excel Ações → Validação → Snapshot Portfolio Atual → PortfolioContext

Excel Opções → Validação → Snapshot Opções Atual → Options / Opportunity Intelligence

Não existe composição do tipo: Snapshot anterior + novo Excel.

## Consequência
O dashboard passa a ter uma única fonte operacional para o estado atual importado pelo usuário, reduzindo o risco de duplicação ou divergência causada por lançamentos manuais.

A infraestrutura de transações existente não é usada pela interface para alterar o snapshot corrente.