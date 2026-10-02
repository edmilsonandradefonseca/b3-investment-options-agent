type Obj = Record<string, unknown>;
const object = (v: unknown): Obj | null => v !== null && typeof v === 'object' && !Array.isArray(v) ? v as Obj : null;
const rows = (v: unknown): Obj[] => Array.isArray(v) ? v.map(object).filter((x): x is Obj => x !== null) : [];
const text = (v: unknown) => typeof v === 'string' ? v : 'Indisponível';
const number = (v: unknown) => typeof v === 'number' && Number.isFinite(v) ? v : null;
const money = (v: unknown) => { const n=number(v); return n === null ? 'Indisponível' : new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(n); };

export default function PersonalHistory({ value }: { value: unknown }) {
  const payload=object(value);
  if(!payload)return null;
  const contexts=typeof payload.status === 'string' ? [['Seleção',payload] as const] : Object.entries(payload).map(([key,v])=>[key,object(v)] as const).filter((v): v is readonly [string,Obj]=>v[1] !== null);
  if(!contexts.length)return null;
  return <section className="analysis-section">
    <h4>Operações pessoais · evidência disponível</h4>
    <p className="muted">Execuções observadas nas bases existentes. Fluxo de caixa não representa lucro total. Frequências pessoais não são probabilidades de mercado.</p>
    {contexts.map(([key,history])=><article className="evidence-card" key={key}>
      <h5>{key === 'Seleção' ? text(history.ticker ?? 'Todos os ativos') : key}</h5>
      <p>{history.status === 'NO_MATCHING_EXECUTIONS' ? 'Nenhuma execução correspondente nesta base consultada.' : history.status === 'UNAVAILABLE' ? 'Histórico indisponível nesta consulta.' : `${number(history.execution_count) ?? 'Indisponível'} execução(ões) observada(s).`}</p>
      <dl>
        <div><dt>Cobertura do histórico</dt><dd>{history.coverage === 'UNKNOWN' ? 'Desconhecida' : text(history.coverage)}</dd></div>
        <div><dt>Consulta</dt><dd>{history.mode === 'STRICT_KNOWN_AT_TIME' ? 'Disponível na data solicitada' : history.mode === 'RETROSPECTIVE_AS_LOADED' ? 'Retrospectiva com dados carregados' : 'Indisponível'}</dd></div>
        <div><dt>Data de corte</dt><dd>{text(history.as_of)}</dd></div>
        <div><dt>Fluxo de caixa observado</dt><dd>{money(history.cash_flow_observed)}</dd></div>
        <div><dt>Desfechos aptos a aprendizado</dt><dd>{number(history.learning_sample_size) ?? 'Indisponível'}</dd></div>
        <div><dt>Assignment / expiração / rolagem</dt><dd>Desconhecidos sem evidência independente</dd></div>
        <div><dt>Similaridade validada</dt><dd>{history.validated_similarity == null ? 'Indisponível' : 'Consulte as evidências técnicas'}</dd></div>
      </dl>
      {rows(history.executions).length > 0 && <details><summary>Execuções e fontes</summary><div className="table-wrap"><table><thead><tr><th>Data</th><th>Instrumento</th><th>Direção</th><th>Quantidade</th><th>Preço</th><th>Fluxo de caixa</th><th>Fonte</th></tr></thead><tbody>{rows(history.executions).map((row,index)=><tr key={`${text(row.transaction_id)}:${index}`}><td>{text(row.trade_date)}</td><td>{text(row.symbol)}{row.identity_match === 'UNVERIFIED_OPTION_ROOT' && <small> · vínculo com ativo não confirmado</small>}</td><td>{row.side === 'BUY' ? 'Compra' : row.side === 'SELL' ? 'Venda' : 'Indisponível'}</td><td>{number(row.quantity) ?? 'Indisponível'}</td><td>{money(row.price)}</td><td>{money(row.cash_flow)}</td><td>{text(row.source_ref)}</td></tr>)}</tbody></table></div>{(number(history.execution_details_omitted) ?? 0) > 0 && <p className="muted">Detalhes limitados às últimas execuções; totais fornecidos pelo backend.</p>}</details>}
      {rows(history.net_flat_sequences).length > 0 && <details><summary>Sequências com saldo observado zerado</summary><p className="muted">Saldo inicial assumido como zero e não verificado. Estas sequências não são desfechos econômicos confirmados.</p>{rows(history.net_flat_sequences).map((row,index)=><p key={index}>{text(row.symbol)} · fluxo bruto {money(row.gross_execution_cash_flow)} · desfecho desconhecido</p>)}</details>}
    </article>)}
  </section>;
}
