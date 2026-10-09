import {useState} from 'react';
import {ResponsiveContainer,ScatterChart,Scatter,XAxis,YAxis,CartesianGrid,Tooltip} from 'recharts';
import {num,text,money,percent,Source} from './cockpit';

export default function ObservedRiskChart({points,asOf}:{points:Record<string,unknown>[];asOf:unknown}) {
 const [scale,setScale]=useState('compressed'),[selected,setSelected]=useState('');
 const valid=points.filter(p=>num(p.volatility_60d)!==null&&Number(p.volatility_60d)>=0&&num(p.liquidity)!==null&&Number(p.liquidity)>=0);
 const compress=scale==='compressed';
 const transform=(v:number)=>compress?Math.log1p(v):v;
 const inverse=(v:number)=>compress?Math.expm1(v):v;
 const plot=valid.map(p=>({...p,x:transform(Number(p.volatility_60d)),y:Number(p.liquidity)/1e6}));
 const detail=valid.find(p=>p.ticker===selected);
 const extreme=valid.filter(p=>Number(p.volatility_60d)>1);
 return <section className="panel" aria-labelledby="observed-risk-title">
  <div className="section-head"><h2 id="observed-risk-title">Volatilidade observada × volume financeiro</h2><select aria-label="Escala da volatilidade" value={scale} onChange={e=>setScale(e.target.value)}><option value="compressed">Escala comprimida</option><option value="linear">Escala linear</option></select></div>
  <p className="muted">Cada ponto é um ativo. À esquerda: menor oscilação histórica. Acima: maior volume negociado. Essa comparação não qualifica uma oportunidade por si só.</p>
  <Source asOf={asOf} source="Histórico usado pela triagem; fontes e datas por ativo na tabela abaixo"/>
  <p className="muted">Volatilidade anualizada (60 retornos, fator √252). Volume financeiro médio das últimas 20 observações: média de fechamento × quantidade negociada, em R$ milhões/dia; é uma aproximação, sem medir spread ou profundidade do livro. {compress?'Eixo horizontal comprimido com log(1 + volatilidade); as marcas exibem os percentuais originais. Todos os pontos são preservados.':'Ambos os eixos usam escala linear.'}</p>
  <div style={{height:340}}><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top:20,right:30,bottom:45,left:35}}>
   <CartesianGrid stroke="#203a50"/>
   <XAxis dataKey="x" type="number" domain={[0,'auto']} tickFormatter={v=>percent(inverse(Number(v)))} label={{value:'Volatilidade anualizada (%) · 60 retornos',position:'bottom',offset:20,fill:'#a9c0d2'}}/>
   <YAxis dataKey="y" type="number" domain={[0,'auto']} width={80} tickFormatter={v=>Number(v).toLocaleString('pt-BR',{maximumFractionDigits:0})} label={{value:'Volume médio (R$ mi/dia)',angle:-90,position:'insideLeft',fill:'#a9c0d2'}}/>
   <Tooltip cursor={{strokeDasharray:'3 3'}} content={({active,payload})=>{const p=payload?.[0]?.payload as Record<string,unknown>|undefined;return active&&p?<div style={{background:'#102436',border:'1px solid #45647e',padding:12}}><strong>{text(p.ticker)}</strong><div>Volatilidade anualizada: {percent(p.volatility_60d)}</div><div>Volume médio: {money(p.liquidity)}/dia</div><div>Cotação em: {text(p.quote_as_of)}</div></div>:null}}/>
   <Scatter isAnimationActive={false} name="Ativos observados" data={plot} fill="#41bbff" onClick={p=>setSelected(String(p.payload?.ticker??''))}/>
  </ScatterChart></ResponsiveContainer></div>
  <label>Inspecionar ativo <select aria-label="Inspecionar ativo do gráfico" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Selecione</option>{valid.map(p=><option key={text(p.ticker)} value={text(p.ticker)}>{text(p.ticker)}</option>)}</select></label>
  {detail&&<p role="status"><strong>{text(detail.ticker)}</strong> · volatilidade anualizada {percent(detail.volatility_60d)} · volume médio {money(detail.liquidity)}/dia · cotação em {text(detail.quote_as_of)}. {Array.isArray(detail.source_refs)?detail.source_refs.join(' · '):''}</p>}
  {extreme.length>0&&<p className="muted">Volatilidade anualizada acima de 100%: {extreme.map(p=>`${text(p.ticker)} (${percent(p.volatility_60d)})`).join(' · ')}. Verifique histórico e ajustes por eventos corporativos antes de interpretar esses valores; eles não foram removidos nem corrigidos automaticamente.</p>}
  <p className="muted">Selecionar um ponto ou ativo apenas inspeciona os dados salvos; não solicita nova análise.</p>
 </section>;
}
