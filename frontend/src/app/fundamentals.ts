// Shared by Market Intelligence and Strategy Lab: display the supplied scale.
export function formatFundamental(value: number | null | undefined, unit: string | null | undefined): string {
  if(value == null || !Number.isFinite(value)) return 'Sem valor elegível';
  const number = new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 2});
  if(unit === 'fraction') return new Intl.NumberFormat('pt-BR', {style:'percent', maximumFractionDigits:2}).format(value);
  if(unit === 'percent') return `${number.format(value)}%`;
  if(unit === 'ratio') return `${number.format(value)}×`;
  const currency = unit?.split('/')[0];
  if(currency && /^[A-Z]{3}$/.test(currency)) {
    return new Intl.NumberFormat('pt-BR', {style:'currency', currency}).format(value);
  }
  return `${new Intl.NumberFormat('pt-BR', {maximumFractionDigits:4}).format(value)}${unit ? ` ${unit}` : ' · unidade não informada'}`;
}
