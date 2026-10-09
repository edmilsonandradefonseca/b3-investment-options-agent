import {useState} from 'react';
import {ResponsiveContainer,BarChart,Bar,XAxis,YAxis,CartesianGrid,Tooltip,Legend,ReferenceLine} from 'recharts';
import {obj,rows,num,text,money,State} from './cockpit';

export default function ScenarioChart({value}:{value:unknown}){
 const alternatives=rows(obj(value).alternatives);
 const [hidden,setHidden]=useState<string[]>([]);
 const names=[...new Set(alternatives.flatMap(a=>Object.keys(obj(a.pnl_by_scenario_brl))))];
 const data=names.map(name=>Object.fromEntries([['name',name],...alternatives.map((a,i)=>['series'+i,num(obj(a.pnl_by_scenario_brl)[name])])]));
 if(!names.length)return <State title="Payoff por cenário indisponível">O backend não retornou valores para os cenários informados.</State>;
 return <div className="interactive-chart"><h3>P&amp;L nas hipóteses informadas</h3><div className="chart-controls">{alternatives.map((a,i)=><label key={i}><input type="checkbox" checked={!hidden.includes('series'+i)} onChange={e=>setHidden(v=>e.target.checked?v.filter(k=>k!=='series'+i):[...v,'series'+i])}/>{text(a.label)}</label>)}</div><div className="chart-canvas" role="img" aria-label="P&L canônico por cenário e alternativa"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{left:10,right:15,bottom:15}}><CartesianGrid stroke="#203a50"/><XAxis dataKey="name" stroke="#9bb2c7"/><YAxis tickFormatter={money} width={95} stroke="#9bb2c7"/><Tooltip contentStyle={{background:'#102436',border:'1px solid #45647e'}} formatter={money}/><Legend/><ReferenceLine y={0} stroke="#c0d3e3"/>{alternatives.map((a,i)=>!hidden.includes('series'+i)&&<Bar key={i} isAnimationActive={false} dataKey={'series'+i} name={text(a.label)} fill={['#42b5ff','#bca1ff','#55dfad'][i%3]} radius={[4,4,0,0]}/>)}</BarChart></ResponsiveContainer></div><p className="chart-description">Valores recebidos do backend para cada hipótese. Não interpolamos outros preços nem atribuímos probabilidade ou retorno esperado.</p></div>;
}
