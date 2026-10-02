import { useMemo, useState } from 'react';
import type { BrokerageOperation, PortfolioPosition } from './api/contracts';

const money = (value: number | null | undefined) => value == null ? 'Sem nota conciliada' : new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
type Props = { positions: PortfolioPosition[]; operations: BrokerageOperation[]; ledgerAvailable: boolean; onSelect: (ticker: string) => void };

export default function OptionsWorkspace({positions, operations, ledgerAvailable, onSelect}: Props) {
  const [asset, setAsset] = useState('');
  const [contract, setContract] = useState('');
  const [kind, setKind] = useState('');
  const [year, setYear] = useState('');
  const [month, setMonth] = useState('');
  const [selectedMonth, setSelectedMonth] = useState('');
  const underlying = (ticker: string) => positions.find(p => p.ticker === ticker)?.underlying_ticker || ticker.slice(0, 4);
  const assets = [...new Set([...positions.map(p => p.underlying_ticker || p.ticker.slice(0, 4)), ...operations.map(o => underlying(o.option_ticker))])].sort();
  const contracts = [...new Set([...positions.map(p => p.ticker), ...operations.map(o => o.option_ticker)])].sort();
  const selected = operations.filter(o => (!asset || underlying(o.option_ticker) === asset) && (!contract || o.option_ticker === contract) && (!kind || positions.find(p => p.ticker === o.option_ticker)?.option_type === kind) && (!year || o.trade_date?.startsWith(year)));
  const visible = selected.filter(o => !month || o.trade_date?.slice(0, 7) === month).filter(o => !selectedMonth || o.trade_date?.slice(0, 7) === selectedMonth);
  const open = positions.filter(p => (!asset || p.underlying_ticker === asset) && (!contract || p.ticker === contract) && (!kind || p.option_type === kind));
  const months = useMemo(() => [...new Set(selected.map(o => o.trade_date?.slice(0, 7)).filter((v): v is string => Boolean(v)))].sort(), [operations, asset, contract, kind, year]);
  const maximum = Math.max(1, ...months.map(m => Math.max(...selected.filter(o => o.trade_date?.startsWith(m)).map(o => Math.abs(o.cash_flow || 0)), 0)));
  // Only an unchanged, single-direction note history matching the BTG quantity is attributed to an open lot.
  // Mixed closes, incomplete notes, or a snapshot mismatch leave the opening premium explicitly unknown.
  const opening = (p: PortfolioPosition) => {
    const rows = operations.filter(o => o.option_ticker === p.ticker && (!o.trade_date || !p.expiration_date || o.trade_date <= p.expiration_date));
    const direction = p.quantity < 0 ? 'SELL' : 'BUY';
    const notesMatchPosition = rows.length > 0
      && rows.every(o => o.side === direction && o.cash_flow != null && o.execution_price != null)
      && Math.abs(rows.reduce((sum, o) => sum + (o.side === 'BUY' ? o.quantity : -o.quantity), 0) - p.quantity) <= 0.001;
    if (!notesMatchPosition) return {
      total: null,
      price: p.average_cost,
      priceSource: p.average_cost == null ? null : p.source_ref,
    };
    const noteQuantity = rows.reduce((sum, o) => sum + o.quantity, 0);
    const notePrice = rows.reduce((sum, o) => sum + o.execution_price! * o.quantity, 0) / noteQuantity;
    return {
      total: Math.abs(rows.reduce((sum, o) => sum + (o.cash_flow || 0), 0)),
      price: p.average_cost ?? notePrice,
      priceSource: p.average_cost == null ? 'BTG: notas conciliadas' : p.source_ref,
    };
  };
  const recent = [...visible].reverse();
  return <div className="options-workspace">
    <div className="option-filters">
      <label>Ano<select value={year} onChange={e => {setYear(e.target.value); setSelectedMonth('')}}><option value="">Todos</option>{[...new Set(operations.map(o => o.trade_date?.slice(0, 4)).filter(Boolean))].sort().reverse().map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Ativo<select value={asset} onChange={e => setAsset(e.target.value)}><option value="">Todos</option>{assets.map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Contrato<select value={contract} onChange={e => setContract(e.target.value)}><option value="">Todos</option>{contracts.map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Tipo<select value={kind} onChange={e => setKind(e.target.value)}><option value="">PUT e CALL</option><option>PUT</option><option>CALL</option></select></label>
      <label>Mês<select value={month} onChange={e => {setMonth(e.target.value);setSelectedMonth('')}}><option value="">Todos</option>{months.map(v => <option key={v}>{v}</option>)}</select></label>
    </div>
    <section className="panel"><h2>Fluxo das notas de corretagem por mês</h2><p className="muted">Entradas e saídas brutas nas operações selecionadas. Resultado realizado exige conciliação de abertura, fechamento, exercício e custos.</p>
      <div className="option-bars">{months.map(m => {const sum = selected.filter(o => o.trade_date?.startsWith(m)).reduce((n, o) => n + (o.cash_flow || 0), 0);return <button title={`${m}: ${money(sum)}`} className={selectedMonth === m ? 'option-month active' : 'option-month'} key={m} onClick={() => setSelectedMonth(selectedMonth === m ? '' : m)}><span>{money(sum)}</span><i style={{height: `${Math.max(5, Math.min(120, Math.abs(sum)/maximum*105))}px`, background: sum >= 0 ? '#22c98a' : '#f46f7b'}}/><b>{m.slice(5)}/{m.slice(2, 4)}</b></button>})}</div>
      {!months.length && <p className="muted">{ledgerAvailable ? 'Nenhuma nota encontrada para os filtros.' : 'Ainda não há operações de notas disponíveis neste backend.'}</p>}</section>
    <section className="panel"><h2>Posições em aberto ({open.length})</h2><div className="table-wrap"><table><thead><tr>{['Ativo','Contrato','Tipo','Lado','Quantidade','Strike','Vencimento','Preço de aquisição/venda','Preço atual','Valor total de abertura (notas)','Custo para encerrar','Resultado se encerrada agora'].map(v => <th key={v}>{v}</th>)}</tr></thead><tbody>{open.map(p => {const opened = opening(p); const close = p.market_value == null ? null : Math.abs(p.market_value); const pnl = opened?.total == null || close == null ? null : (p.quantity < 0 ? opened.total - close : close - opened.total);return <tr key={p.position_id} onClick={() => onSelect(p.ticker)}><td>{p.underlying_ticker || '—'}</td><td>{p.ticker}</td><td>{p.option_type}</td><td>{p.quantity < 0 ? 'Vendida' : 'Comprada'}</td><td>{Math.abs(p.quantity)}</td><td>{money(p.strike)}</td><td>{p.expiration_date || '—'}</td><td title={opened?.priceSource || 'Sem preço de aquisição/venda canônico ou notas conciliadas'}>{money(opened?.price)}</td><td>{money(p.market_price)}</td><td>{money(opened?.total)}</td><td>{p.quantity < 0 ? money(close) : '—'}</td><td>{pnl == null ? 'Sem conciliação' : money(pnl)}</td></tr>})}</tbody></table></div></section>
    <section className="panel"><h2>Histórico de operações das notas ({recent.length})</h2><div className="table-wrap"><table><thead><tr>{['Data','Ativo','Contrato','Operação','Quantidade','Preço unitário','Valor recebido / pago','Nota BTG'].map(v => <th key={v}>{v}</th>)}</tr></thead><tbody>{recent.map(o => <tr key={o.transaction_id} title={o.source_ref} onClick={() => onSelect(o.option_ticker)}><td>{o.trade_date || '—'}</td><td>{underlying(o.option_ticker)}</td><td>{o.option_ticker}</td><td>{o.side === 'SELL' ? 'Venda' : 'Compra'}</td><td>{o.quantity}</td><td>{money(o.execution_price)}</td><td>{money(o.cash_flow)}</td><td>{o.note_number || '—'}</td></tr>)}</tbody></table></div></section>
  </div>;
}
