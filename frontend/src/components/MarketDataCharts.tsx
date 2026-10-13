import {useEffect,useMemo,useState} from "react";
import type {ReactNode} from "react";
import {b3Api} from "../api/client";
import {invoke,isTauri} from "@tauri-apps/api/core";
import type {YieldCurveResponse} from "../api/contracts";
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

export function LineChart({values,color,zero=false,label,xLabel,yLabel,xFormat=numberLabel,yFormat=numberLabel}:{values:XY[];color:string;zero?:boolean;label:string;xLabel:string;yLabel:string;xFormat?:(value:number)=>string;yFormat?:(value:number)=>string}){
 const width=900,height=300,left=88,right=24,top=24,bottom=68;
 if(values.length<2)return <State kind="limited" title="Amostra insuficiente para o gráfico">A fonte não trouxe pontos suficientes para desenhar a série.</State>;
 const ys=values.map(point=>point.y);
 const min=Math.min(...ys,zero?0:Infinity),max=Math.max(...ys,zero?0:-Infinity);
 const range=max-min||1;
 const minX=values[0].x,maxX=values[values.length-1].x,xRange=maxX-minX||1;
 const plotWidth=width-left-right,plotHeight=height-top-bottom;
 const px=(x:number)=>left+((x-minX)/xRange)*plotWidth;
 const py=(y:number)=>height-bottom-((y-min)/range)*plotHeight;
 const path=values.map((point,index)=>`${index===0?"M":"L"} ${px(point.x).toFixed(1)} ${py(point.y).toFixed(1)}`).join(" ");
 const baseline=zero?py(0):null;
 const ticks=Array.from({length:5},(_,index)=>index/4);
 return <svg style={{width:"100%",height:"auto",minHeight:"230px",display:"block"}} role="img" aria-label={label} viewBox={`0 0 ${width} ${height}`} className="market-series-chart">
  <title>{label}</title>
  {ticks.map(fraction=>{const value=min+fraction*range,y=py(value);return <g key={`y-${fraction}`}>
   <line x1={left} x2={width-right} y1={y} y2={y} stroke="#294258" strokeDasharray="3 5"/>
   <text x={left-12} y={y+5} textAnchor="end" fill="#b4c9da" fontSize="14">{yFormat(value)}</text>
  </g>})}
  <line x1={left} x2={left} y1={top} y2={height-bottom} stroke="#607b90"/>
  <line x1={left} x2={width-right} y1={height-bottom} y2={height-bottom} stroke="#607b90"/>
  {ticks.map(fraction=>{const value=minX+fraction*xRange,x=px(value);return <g key={`x-${fraction}`}>
   <line x1={x} x2={x} y1={height-bottom} y2={height-bottom+6} stroke="#607b90"/>
   <text x={x} y={height-bottom+25} textAnchor={fraction===0?"start":fraction===1?"end":"middle"} fill="#b4c9da" fontSize="14">{xFormat(value)}</text>
  </g>})}
  <text x={left+plotWidth/2} y={height-12} textAnchor="middle" fill="#b4c9da" fontSize="15">{xLabel}</text>
  <text transform={`translate(20 ${top+plotHeight/2}) rotate(-90)`} textAnchor="middle" fill="#b4c9da" fontSize="15">{yLabel}</text>
  {baseline!==null&&<line x1={left} x2={width-right} y1={baseline} y2={baseline} stroke="#607b90" strokeDasharray="4 5"/>}
  <path d={path} fill="none" stroke={color} strokeWidth="3" vectorEffect="non-scaling-stroke"/>
  {values.map((point,index)=><circle key={index} cx={px(point.x)} cy={py(point.y)} r="6" fill="transparent"><title>{`${xLabel}: ${xFormat(point.x)} · ${yLabel}: ${yFormat(point.y)}`}</title></circle>)}
 </svg>;
}

function ChartPanel({title,subtitle,children}:{title:string;subtitle:string;children:ReactNode}){
 return <section className="panel market-series-panel"><div className="section-head"><div><h3>{title}</h3><p className="muted">{subtitle}</p></div></div>{children}</section>;
}

export default function MarketDataCharts(){
 const [externalError,setExternalError]=useState("");
 const openForeignFlow=async()=>{setExternalError("");try{if(isTauri()){await invoke("open_foreign_flow");}else{window.open("https://fluxos.investfy.com/?tab=chart&period=ytd&investor=foreigners&chart=column&ma=28","_blank","noopener,noreferrer");}}catch{setExternalError("Não foi possível abrir o navegador. Use o link abaixo.");}};
 const [curve,setCurve]=useState<CurveCode>("PRE"),[curveData,setCurveData]=useState<YieldCurveResponse|null>(null),[curveError,setCurveError]=useState(""),[curveBusy,setCurveBusy]=useState(false);
 const [revision,setRevision]=useState(0);
 useEffect(()=>{let active=true;setCurveBusy(true);setCurveError("");b3Api.yieldCurve(curve).then(data=>{if(active)setCurveData(data)}).catch(error=>{if(active)setCurveError(error instanceof Error?error.message:String(error))}).finally(()=>{if(active)setCurveBusy(false)});return()=>{active=false}},[curve,revision]);

 const curveRows=useMemo(()=>[...(curveData?.observations??[])].sort((a,b)=>a.days_calendar-b.days_calendar),[curveData]);
 const curveValues=curveRows.map(item=>({x:item.days_calendar,y:item.rate_percent_per_year}));
 const latestCurve=curveRows[0];
 const curveDescription=curve==="PRE"?"DI × prefixado":curve==="DIC"?"DI × IPCA":"Cupom limpo em dólar";

 return <div className="market-series-grid" style={{display:"grid",gap:"1rem"}}>
  <ChartPanel title="Fluxo do investidor estrangeiro" subtitle="Investfy · consulta em outra janela">
   <p className="muted">Consulte o gráfico de investidores estrangeiros no Investfy.</p>
   <button type="button" onClick={()=>void openForeignFlow()}>Abrir fluxo de estrangeiros ↗</button>
   <p className="muted">Abre no navegador com período acumulado no ano, gráfico de colunas e média móvel de 28 períodos.</p>
   {externalError&&<State kind="error" title="Abertura indisponível">{externalError} <a href="https://fluxos.investfy.com/?tab=chart&period=ytd&investor=foreigners&chart=column&ma=28" target="_blank" rel="noopener noreferrer">Abrir Investfy</a></State>}
  </ChartPanel>

  <ChartPanel title="Curva de juros" subtitle={`B3 TaxaSwap · ${curveDescription} · ${curveData?.as_of?dateLabel(curveData.as_of):"data indisponível"}`}>
   <button type="button" className="ghost" disabled={curveBusy} onClick={()=>setRevision(value=>value+1)}>{curveBusy?"Atualizando…":"Atualizar curva"}</button>
   <label className="curve-selector">Curva<select aria-label="Selecionar curva de juros" value={curve} onChange={event=>{setCurveData(null);setCurveError("");setCurve(event.target.value as CurveCode)}}><option value="PRE">DI × Pré (PRE)</option><option value="DIC">DI × IPCA (DIC)</option><option value="DCL">Cupom limpo dólar (DCL)</option></select></label>
   {curveBusy&&!curveData?<State kind="loading" title="Consultando curva">Buscando vértices publicados pela B3.</State>:<>
    {curveError&&<State kind="error" title={curveRows.length?"Falha ao atualizar · dados anteriores preservados":"Consulta de curva indisponível"}>{curveError}</State>}
    {!curveRows.length?(curveError?null:<State kind="limited" title="Sem vértices disponíveis">A fonte não retornou observações para esta curva.</State>):<>
     <div className="market-series-metric" style={{display:"flex",flexDirection:"column",gap:".25rem",padding:".5rem 0"}}><strong>{numberLabel(latestCurve?.rate_percent_per_year)}% a.a.</strong><span>primeiro vértice · {latestCurve?.days_calendar} dias corridos · {latestCurve?.days_business} dias úteis</span></div>
     <LineChart values={curveValues} color="#47d7a0" label={`Curva ${curve} em percentual ao ano por dias corridos`} xLabel="Prazo (dias corridos)" yLabel="Taxa (% a.a.)" xFormat={value=>Math.round(value).toLocaleString("pt-BR")} yFormat={value=>`${numberLabel(value)}%`}/>
     <p className="muted">Fonte: B3 TaxaSwap, interpretada pelo parser do pyettj · taxa em % a.a. · eixo horizontal em dias corridos. As curvas são identificadas pelo código publicado; DIC é DI × IPCA.</p>
    </>}
   </>}
  </ChartPanel>
 </div>;
}
