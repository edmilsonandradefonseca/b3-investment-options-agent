import type { ReactNode } from 'react';
export type Obj = Record<string, unknown>;
export const obj=(v:unknown):Obj=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Obj:{};
export const rows=(v:unknown):Obj[]=>Array.isArray(v)?v.map(obj):[];
export const num=(v:unknown):number|null=>typeof v==='number'&&Number.isFinite(v)?v:null;
export const text=(v:unknown):string=>typeof v==='string'?v:'Indisponível';
export const money=(v:unknown)=>num(v)===null?'Indisponível':new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(num(v)!);
export const percent=(v:unknown)=>num(v)===null?'Indisponível':new Intl.NumberFormat('pt-BR',{style:'percent',maximumFractionDigits:2}).format(num(v)!);
export const date=(v:unknown)=>{
 if(typeof v!=='string'||!v||Number.isNaN(Date.parse(v)))return 'Indisponível';
 const dayOnly=v.length===10;
 return new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',...(dayOnly?{}:{timeStyle:'short' as const}),timeZone:'America/Sao_Paulo'}).format(new Date(dayOnly?v+'T12:00:00Z':v));
};
export function State({title,children,kind='empty'}:{title:string;children:ReactNode;kind?:string}){return <div className={`product-state ${kind}`} role={kind==='error'?'alert':'status'}><span className="state-glyph">{kind==='loading'?'◌':kind==='error'?'!':'◇'}</span><div><strong>{title}</strong><p>{children}</p></div></div>}
export function Metric({label,value,detail}:{label:string;value:ReactNode;detail?:ReactNode}){return <article className="metric"><span>{label}</span><strong>{value}</strong>{detail&&<small>{detail}</small>}</article>}
export function Source({asOf,source}:{asOf:unknown;source?:string}){return <div className="source-line"><span>Dados de {date(asOf)}</span>{source&&<details><summary>Fonte</summary><p>{source}</p></details>}</div>}
