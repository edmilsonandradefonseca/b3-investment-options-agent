import { useEffect, useMemo, useState } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { b3Api } from '../api/client';
import type { LiveAnalysisResponse, StockMarketData } from '../api/contracts';
import { State, date, money } from './cockpit';

type Period = '1W' | '1M' | '1Y';
type Point = Record<string, string | number>;
const periods: Array<{ id: Period; label: string; days: number }> = [
  { id: '1W', label: '1 semana', days: 7 },
  { id: '1M', label: '1 mês', days: 30 },
  { id: '1Y', label: '1 ano', days: 365 },
];
const colors = ['#42b5ff', '#efba59'];

function tickersIn(question: string): string[] {
  return Array.from(new Set(question.toUpperCase().match(/\b[A-Z]{4}\d{1,2}\b/g) ?? [])).slice(0, 2);
}

function historyOf(response: LiveAnalysisResponse): StockMarketData[] {
  return response.market.price_history ?? [];
}

export default function StrategyHistoryChart({ question }: { question: string }) {
  const tickers = useMemo(() => tickersIn(question), [question]);
  const [period, setPeriod] = useState<Period>('1M');
  const [series, setSeries] = useState<Record<string, StockMarketData[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setSeries({});
    setError('');
    if (!tickers.length) return;
    setLoading(true);
    Promise.allSettled(tickers.map(ticker => b3Api.liveAnalysis(ticker)))
      .then(results => {
        if (cancelled) return;
        const loaded: Record<string, StockMarketData[]> = {};
        const failures: string[] = [];
        results.forEach((result, index) => {
          const ticker = tickers[index];
          if (result.status === 'fulfilled') loaded[ticker] = historyOf(result.value);
          else failures.push(ticker);
        });
        setSeries(loaded);
        setError(failures.length ? 'Histórico indisponível para: ' + failures.join(', ') : '');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [tickers.join('|')]);

  const selectedPeriod = periods.find(item => item.id === period)!;
  const chart = useMemo(() => {
    if (!tickers.length) return { rows: [] as Point[], basis: 'close' as 'close' | 'adjusted_close', since: '', until: '' };
    const all = tickers.flatMap(ticker => series[ticker] ?? []);
    if (!all.length) return { rows: [] as Point[], basis: 'close' as 'close' | 'adjusted_close', since: '', until: '' };
    const basis: 'close' | 'adjusted_close' = all.every(row =>
      typeof row.adjusted_close === 'number' && Number.isFinite(row.adjusted_close) && row.adjusted_close > 0
    ) ? 'adjusted_close' : 'close';
    const latest = Math.max(...all.map(row => Date.parse(row.observation_timestamp)).filter(Number.isFinite));
    const cutoff = latest - selectedPeriod.days * 86400000;
    const byTicker = tickers.map(ticker => {
      const map = new Map<string, number>();
      for (const row of series[ticker] ?? []) {
        const timestamp = Date.parse(row.observation_timestamp);
        const value = basis === 'adjusted_close' ? row.adjusted_close : row.close;
        if (Number.isFinite(timestamp) && timestamp >= cutoff && typeof value === 'number' && Number.isFinite(value) && value > 0) {
          map.set(row.observation_timestamp.slice(0, 10), value);
        }
      }
      return map;
    });
    let rows: Point[] = [];
    if (tickers.length === 1) {
      rows = Array.from(byTicker[0].entries()).sort(([a], [b]) => a.localeCompare(b))
        .map(([dateValue, value]) => ({ date: dateValue, [tickers[0]]: value }));
    } else {
      const commonDates = Array.from(byTicker[0].keys()).filter(day => byTicker[1].has(day)).sort();
      const firstLeft = commonDates.map(day => byTicker[0].get(day)!).find(value => value > 0);
      const firstRight = commonDates.map(day => byTicker[1].get(day)!).find(value => value > 0);
      if (firstLeft && firstRight) {
        rows = commonDates.map(day => ({
          date: day,
          [tickers[0]]: (byTicker[0].get(day)! / firstLeft) * 100,
          [tickers[1]]: (byTicker[1].get(day)! / firstRight) * 100,
        }));
      }
    }
    return {
      rows,
      basis,
      since: rows.length ? String(rows[0].date) : '',
      until: rows.length ? String(rows[rows.length - 1].date) : '',
    };
  }, [tickers.join('|'), series, selectedPeriod.days]);

  if (!tickers.length) return null;
  return <section className="panel" aria-label="Gráfico histórico do Strategy Lab">
    <div className="section-head">
      <div><h3>Histórico de preços</h3><p className="muted">{tickers.length === 2 ? 'Comparação em datas comuns, normalizada para base 100.' : 'Preço histórico do ativo analisado.'}</p></div>
      <div className="action-row" role="group" aria-label="Período do gráfico">
        {periods.map(item => <button key={item.id} type="button" className={period === item.id ? 'selected' : 'secondary'} aria-pressed={period === item.id} onClick={() => setPeriod(item.id)}>{item.label}</button>)}
      </div>
    </div>
    {loading && <State kind="loading" title="Carregando histórico">Consultando a série disponível para {tickers.join(' e ')}.</State>}
    {error && <State kind="limited" title="Cobertura parcial do gráfico">{error}. A série disponível continua exibida.</State>}
    {!loading && chart.rows.length >= 2 && <>
      <p className="muted">{chart.since} a {chart.until} · {chart.rows.length} sessões · {chart.basis === 'adjusted_close' ? 'fechamento ajustado' : 'fechamento bruto'}{tickers.length === 2 ? ' · base 100' : ''}</p>
      <div className="chart-canvas" role="img" aria-label={'Histórico de ' + tickers.join(' e ')} style={{ height: 300 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chart.rows} margin={{ top: 12, right: 20, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#203a50" strokeDasharray="3 5" />
            <XAxis dataKey="date" tickFormatter={value => date(value).slice(0, 10)} minTickGap={45} stroke="#9bb2c7" />
            <YAxis domain={['auto', 'auto']} stroke="#9bb2c7" tickFormatter={value => tickers.length === 1 ? money(value) : Number(value).toFixed(0)} />
            <Tooltip contentStyle={{ background: '#102436', border: '1px solid #45647e', borderRadius: 8 }} labelFormatter={value => date(value)} formatter={(value, name) => [tickers.length === 1 ? money(value) : Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 }), String(name)]} />
            <Legend />
            {tickers.map((ticker, index) => <Line key={ticker} type="linear" dataKey={ticker} name={ticker} stroke={colors[index]} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />)}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>}
    {!loading && !error && chart.rows.length < 2 && <State kind="limited" title="Histórico insuficiente">Não há duas sessões comuns nesta janela para montar o gráfico.</State>}
    <p className="muted">A comparação usa fechamento nas mesmas sessões e base 100; ela mostra a variação histórica observada, não prevê retorno futuro.</p>
  </section>;
}
