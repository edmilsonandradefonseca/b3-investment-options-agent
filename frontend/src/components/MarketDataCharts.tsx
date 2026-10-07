import {useEffect,useMemo,useState} from "react";
import type {ReactNode} from "react";
import {b3Api} from "../api/client";
import type {InvestorFlowObservation,InvestorFlowResponse,YieldCurveResponse} from "../api/contracts";
import {State} from "./cockpit";

type CurveCode = "PRE" | "DIC" | "DCL";
type XY = {x:number;y:number};

function dateLabel(value?:string|null):string{
 if(!value)return "Data indisponível";
 const parsed=new Date(value);
 return Number.isNaN(parsed.getTime())?"Data indisponível":parsed.toLocaleDateString("pt-BR",{timeZone:"UTC"});
}

function numberLabel(value:number|null|undefined):string{
 if(typeof value!=="number"||!Number.isFinite(value))return "Indisponível";
 return value.toLocaleString("pt-BR",{maximumFractionDigits:2});
}

function LineChart({values,color,zero=false,label}:{values:XY[];color:string;zero?:boolean;label:string}){
 const width=900,height=230,pad=24;
 if(values.length<2)return <State kind="limited" title="Amostra insuficiente para o gráfico">A fonte não trouxe pontos suficientes para desenhar a série.</State>;
 const ys=values.map(point=>point.y);
 const min=Math.min(...ys,zero?0:Infinity),max=Math.max(...ys,zero?0:-Infinity);
 const range=max-min||1;
 const minX=values[0].x,maxX=values[values.length-1].x,xRange=maxX-minX||1;
 const points=values.map(point=>({
  x:pad+((point.x-minX)/xRange)*(width-pad*2),
  y:height-pad-((point.y-min)/range)*(height-pad*2),
 }));
 const path=points.map((point,index)=>`${index===0?"M":"L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");
 const baseline=zero?height-pad-((0-min)/range)*(height-pad*2):null;
 return <svg style={{width:"100%",height:"230px",display:"block"}} role="img" aria-label={label} viewBox={`0 0 ${width} ${height}`} className="market-series-chart" preserveAspectRatio="none">
  <line x1={pad} x2={width-pad} y1={height-pad} y2={height-pad} stroke="#294258"/>
  {baseline!==null&&<line x1={pad} x2={width-pad} y1={baseline} y2={baseline} stroke="#607b90" strokeDasharray="4 5"/>}
  <path d={path} fill="none" stroke={color} strokeWidth="3" vectorEffect="non-scaling-stroke"/>
 </svg>;
}

function ChartPanel({title,subtitle,children}:{title:string;subtitle:string;children:ReactNode}){
 return <section className="panel market-series-panel"><div className="section-head"><div><h3>{title}</h3><p className="muted">{subtitle}</p></div></div>{children}</section>;
}

export default function MarketDataCharts(){
 const [flows,setFlows]=useState<InvestorFlowResponse|null>(null),[flowError,setFlowError]=useState(""),[flowBusy,setFlowBusy]=useState(false);
 const [curve,setCurve]=useState<CurveCode>("PRE"),[curveData,setCurveData]=useState<YieldCurveResponse|null>(null),[curveError,setCurveError]=useState(""),[curveBusy,setCurveBusy]=useState(false);
 const [revision,setRevision]=useState(0);
 useEffect(()=>{let active=true;setFlowBusy(true);setFlowError("");b3Api.investorFlows().then(data=>{if(active)setFlows(data)}).catch(error=>{if(active)setFlowError(error instanceof Error?error.message:String(error))}).finally(()=>{if(active)setFlowBusy(false)});return()=>{active=false}},[revision]);
 useEffect(()=>{let active=true;setCurveBusy(true);setCurveError("");b3Api.yieldCurve(curve).then(data=>{if(active)setCurveData(data)}).catch(error=>{if(active)setCurveError(error instanceof Error?error.message:String(error))}).finally(()=>{if(active)setCurveBusy(false)});return()=>{active=false}},[curve,revision]);

 const foreign=useMemo(()=>[...(flows?.observations??[])]
  .filter((item:InvestorFlowObservation)=>item.investor_type==="FOREIGN"&&typeof item.net_financial_value==="number"&&item.observation_date)
  .sort((a,b)=>String(a.observation_date).localeCompare(String(b.observation_date))),[flows]);
 const recentForeign=foreign.slice(-180);
 const flowValues=recentForeign.map((item,index)=>({x:index,y:item.net_financial_value as number}));
 const curveRows=useMemo(()=>[...(curveData?.observations??[])].sort((a,b)=>a.days_calendar-b.days_calendar),[curveData]);
 const curveValues=curveRows.map(item=>({x:item.days_calendar,y:item.rate_percent_per_year}));
 const latestForeign=foreign.at(-1);
 const latestCurve=curveRows[0];
 const curveDescription=curve==="PRE"?"DI × prefixado":curve==="DIC"?"DI × IPCA":"Cupom limpo em dólar";

 return <div className="market-series-grid" style={{display:"grid",gap:"1rem"}}>
  <ChartPanel title="Fluxo do investidor estrangeiro" subtitle={`Dados de Mercado · série diária · ${foreign.length} observações`}>
   <button type="button" className="ghost" disabled={flowBusy} onClick={()=>setRevision(value=>value+1)}>{flowBusy?"Atualizando…":"Atualizar"}</button>
   {flowBusy&&!flows?<State kind="loading" title="Consultando fluxo">Buscando série diária no provedor.</State>:<>
    {flowError&&<State kind="error" title="Falha ao atualizar · dados anteriores preservados">{flowError}</State>}
    {flows?.status==="NO_DATA"||!foreign.length?<State kind="limited" title="Sem observações de fluxo">A API não retornou a categoria estrangeiros para este período.</State>:<>
     <div className="market-series-metric" style={{display:"flex",flexDirection:"column",gap:".25rem",padding:".5rem 0"}}><strong>{numberLabel(latestForeign?.net_financial_value)}</strong><span>valor mais recente · {dateLabel(latestForeign?.observation_date)}</span></div>
     <LineChart values={flowValues} color="#43b7ff" zero label="Fluxo diário reportado de investidores estrangeiros"/>
     <p className="muted">Fonte: Dados de Mercado · unidade não declarada no esquema da API; valor exibido sem conversão ou símbolo monetário. O gráfico mostra o campo reportado, não uma decomposição de compras e vendas.</p>
    </>}
   </>}
  </ChartPanel>

  <ChartPanel title="Curva de juros" subtitle={`B3 TaxaSwap · ${curveDescription} · ${curveData?.as_of?dateLabel(curveData.as_of):"data indisponível"}`}>
   <label className="curve-selector">Curva<select aria-label="Selecionar curva de juros" value={curve} onChange={event=>{setCurveData(null);setCurveError("");setCurve(event.target.value as CurveCode)}}><option value="PRE">DI × Pré (PRE)</option><option value="DIC">DI × IPCA (DIC)</option><option value="DCL">Cupom limpo dólar (DCL)</option></select></label>
   {curveBusy&&!curveData?<State kind="loading" title="Consultando curva">Buscando vértices publicados pela B3.</State>:<>
    {curveError&&<State kind="error" title="Falha ao atualizar · dados anteriores preservados">{curveError}</State>}
    {!curveRows.length?<State kind="limited" title="Sem vértices disponíveis">A fonte não retornou observações para esta curva.</State>:<>
     <div className="market-series-metric" style={{display:"flex",flexDirection:"column",gap:".25rem",padding:".5rem 0"}}><strong>{numberLabel(latestCurve?.rate_percent_per_year)}% a.a.</strong><span>primeiro vértice · {latestCurve?.days_calendar} dias corridos · {latestCurve?.days_business} dias úteis</span></div>
     <LineChart values={curveValues} color="#47d7a0" label={`Curva ${curve} em percentual ao ano por dias corridos`}/>
     <p className="muted">Fonte: B3 TaxaSwap, interpretada pelo parser do pyettj · taxa em % a.a. · eixo horizontal em dias corridos. As curvas são identificadas pelo código publicado; DIC é DI × IPCA.</p>
    </>}
   </>}
  </ChartPanel>
 </div>;
}
