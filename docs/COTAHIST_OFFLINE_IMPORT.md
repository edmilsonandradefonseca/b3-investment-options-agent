# Importação offline do histórico B3

Baixe os arquivos anuais COTAHIST_AAAA.ZIP da [página de cotações históricas da B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/). O arquivo do ano corrente contém dados acumulados até o último dia útil publicado pela B3.

Exemplo no servidor Ubuntu:

```bash
mkdir -p ~/b3-historico
curl -fL --retry 3 --progress-bar \
  -o ~/b3-historico/COTAHIST_A2026.ZIP \
  'https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A2026.ZIP'
unzip -t ~/b3-historico/COTAHIST_A2026.ZIP | tail -1
```

O importador fica em modo de simulação por padrão. Execute a partir de um checkout que contenha a versão atual da branch feat/cotahist-offline-import:

```bash
PYTHONPATH=/tmp/b3-cotahist-validation/src \
  /opt/b3-investment-options-agent/.venv/bin/python \
  /tmp/b3-cotahist-validation/scripts/import_cotahist.py \
  --zip /home/edmilson/b3-historico/COTAHIST_A2026.ZIP \
  --tickers PETR4,VALE3,ITUB4,WEGE3
```

Revise os totais por código. Se o dry-run estiver correto, repita o comando com --apply sob o ambiente systemd da produção, usando B3_AGENT_PROJECT_ROOT=/opt/b3-investment-options-agent e B3_AGENT_DATA_DIR=/opt/b3-runtime/data. O destino é /opt/b3-runtime/data/archive/cotahist_raw. O importador mescla por código e pregão, então repetir 2025 ou 2026 não duplica pregões.

O endpoint ao vivo lê primeiro esse arquivo local e consulta o cache BRAPI apenas para cobrir datas fora do arquivo, como pregões recentes. OPLAB continua fornecendo a cadeia de opções. A carga de 2026 é necessária para que o arquivo cubra a janela atual de 120 dias; 2025 sozinho fica fora dessa janela.

O COTAHIST contém preços **não ajustados**. Use os dados para histórico de preços, não para retorno total ou dividendos. O importador grava em Parquet; não grava a série histórica de preços no SQLite.
