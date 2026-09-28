# Offline B3 historical-price import

Use B3's annual `COTAHIST_AAAA.ZIP` files, downloaded from the [historical quotes page](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/). The importer streams the ZIP directly; it does not call BRAPI or OPLAB.

```bash
cd /opt/b3-investment-options-agent
.venv/bin/python scripts/import_cotahist.py \
  --zip /path/to/COTAHIST_A2025.ZIP \
  --tickers PETR4,VALE3,ITUB4,WEGE3
```

The default is a dry run. Review `records_by_ticker`, then add `--apply`. Repeat for each year. Reimporting the same year replaces the same ticker/date records without duplicating dates.

Only selected cash-market (`TPMERC=010`) records denominated in BRL are written to `data/archive/cotahist_raw/ticker=.../market.parquet` (or under `B3_AGENT_DATA_DIR` when set). Other records are skipped. The archive remains separate from the operational BRAPI cache.

**Prices are raw and unadjusted.** The importer divides B3's implicit two-decimal price fields by the quotation factor and marks every record `UNADJUSTED`. It leaves `adjusted_close` empty. Do not use this archive to calculate total return or feed current-price recommendations. The source has no publication timestamp, so `available_timestamp` is estimated as the next midnight in São Paulo and explicitly marked `AVAILABILITY_ESTIMATED`; backtests needing exact point-in-time availability require a stronger source.

Start with the assets actually used in the portfolio or watchlist and one annual ZIP. Compare selected prices and row counts with the original B3 file before importing more years. Monitor archive size independently from the operational retention window.
