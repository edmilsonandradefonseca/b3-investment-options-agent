# Provider Evaluation v1

## 1. Objetivo

Avaliar fontes de dados para o B3 Investment & Options Agent antes de
implementar integrações definitivas.

A estratégia adotada é:

> FREE-FIRST

O sistema deve utilizar fontes gratuitas sempre que elas atenderem aos
requisitos de qualidade, cobertura, histórico e Point-in-Time.

Uma fonte paga somente será considerada quando existir um gap comprovado
que seja relevante para uma decisão do sistema.

---

## 2. Estratégia de custo

Prioridade:

1. Dados gratuitos
2. Dados públicos oficiais
3. Providers gratuitos com API
4. Providers pagos somente quando necessário

Nenhuma assinatura ou API paga será contratada nesta fase.

---

## 2. Candidates

### 2.1 brapi Free

Status: PRIMARY DEVELOPMENT CANDIDATE

Custo inicial: R$ 0

Possíveis usos:

- cotações
- histórico
- fundamentos
- dividendos
- JCP
- informações de empresas
- dados de opções disponíveis no plano gratuito

Pontos a validar:

- cobertura real
- limites do plano gratuito
- histórico
- qualidade dos dados
- disponibilidade temporal
- Point-in-Time
- cobertura de opções
- open interest
- IV
- Greeks
- histórico de opções

---
### 2.2 OpLab

Status: PRIMARY OPTIONS DEVELOPMENT CANDIDATE

Uso inicial:

- opções B3
- cadeia de opções
- PUT/CALL
- strike
- vencimento
- bid/ask
- volume
- open interest
- IV
- Greeks
- métricas derivadas disponibilizadas pelo provider

Pontos a validar:

- cobertura
- histórico
- timestamps
- Point-in-Time
- open interest
- IV
- Greeks
- liquidez
- limites da API
- estabilidade
- licença
- plano contratado

OpLab será inicialmente utilizado como provider especializado
de opções, mantendo o restante do sistema independente da API.

### 2.3 B3 Public Data

Status: OFFICIAL COMPLEMENTARY SOURCE

Custo inicial: R$ 0

Uso:

- validação
- referência oficial
- informações públicas
- complementação de gaps

Limitação:

Os produtos/API comerciais da B3 podem exigir contratação específica.

---

### 2.4 Banco Central / Dados Públicos

Status: MACRO SOURCE

Custo inicial: R$ 0

Possíveis dados:

- SELIC
- IPCA
- câmbio
- indicadores macroeconômicos

Uso:

MacroObservation.

---

### 2.5 Other Free Sources

Status: FALLBACK / EXPERIMENTAL

Serão avaliadas somente quando:

- houver um gap específico
- o dado for relevante
- a fonte tiver qualidade suficiente

---

## 3. Paid Providers

Providers pagos NÃO serão utilizados automaticamente.

Exemplos de candidatos futuros:

- Economatica
- B3 commercial data products
- outros providers especializados

Eles somente avançarão quando um gap técnico ou de qualidade for
documentado.

---

## 4. Provider Evaluation Criteria

Cada provider será avaliado em:

1. Market data
2. Fundamentals
3. Corporate actions
4. Options
5. Open interest
6. IV
7. Greeks
8. Historical data
9. Point-in-Time
10. Provenance
11. Data quality
12. Coverage
13. Stability
14. Rate limits
15. Cost
16. Licensing
17. API quality
18. Python integration
19. Fallback suitability

---

## 5. Critical Requirements

Para nosso sistema, são CRITICAL:

### Stocks

- OHLC
- volume
- historical data
- corporate actions
- timestamps

### Fundamentals

- financial statements
- reporting period
- publication date
- availability date
- historical values

### Options

- option identifier
- underlying
- PUT/CALL
- strike
- expiration
- bid
- ask
- last
- volume
- open interest
- IV
- Greeks

### Point-in-Time

Devemos conseguir determinar:

"What was actually knowable at decision timestamp T?"

Se não conseguirmos responder essa pergunta, o provider não poderá ser
utilizado como única fonte para backtesting histórico.

---

## 6. Preliminary Ranking

### Development

1. brapi Free
2. Public B3 data
3. Banco Central / public macro data
4. Other free sources
5. Paid providers only if required

### Production

Ainda NÃO definido.

A decisão de produção será tomada somente depois dos testes.

---

## 7. Free-First Rule

Antes de adicionar qualquer provider pago:

1. identificar o gap
2. documentar o gap
3. verificar se outra fonte gratuita resolve
4. verificar se podemos derivar o dado localmente
5. avaliar impacto na decisão
6. estimar custo
7. somente então considerar provider pago

---

## 8. Local Computation

Sempre que possível, dados simples serão derivados localmente.

Exemplos:

- SMA
- EMA
- RSI
- MACD
- ATR
- retornos
- volatilidade histórica
- valuation ratios
- option yield
- payoff
- annualized return

Não pagar por dados que podemos calcular corretamente a partir dos dados
primários disponíveis.

---

## 9. Options Strategy

Como SELL PUT e SELL COVERED CALL são componentes centrais do sistema,
opções terão prioridade especial na avaliação.

Precisamos validar se fontes gratuitas fornecem dados suficientes para:

### SELL PUT

- strike
- expiration
- premium
- bid/ask
- volume
- open interest
- IV
- Greeks
- underlying price

### SELL CALL

- strike
- expiration
- premium
- bid/ask
- volume
- open interest
- IV
- Greeks
- underlying price
- current position

Se algum desses dados não estiver disponível gratuitamente,
o gap deverá ser documentado antes de considerar uma fonte paga.

---

## 10. Point-in-Time Risk

O maior risco da utilização de fontes gratuitas não é somente precisão.

É:

> LOOK-AHEAD BIAS

Devemos verificar se dados históricos podem ser reconstruídos como eram
conhecidos na época.

Exemplos de risco:

- fundamentos revisados
- corporate actions ajustadas retrospectivamente
- históricos modificados
- opções históricas inexistentes
- timestamps inadequados

---

## 11. Validation Strategy

O provider será testado utilizando pelo menos:

- PETR4
- VALE3
- ITUB4

Para cada ativo serão avaliados:

- market data
- fundamentals
- corporate actions
- options
- timestamps
- provenance

---

## 12. Provider Adapter

Cada fonte deverá implementar:

Provider
→ Adapter
→ Data Contract

O restante do sistema não poderá depender da API específica.

---

## 13. No Premature Integration

Nesta etapa não será implementada uma integração definitiva.

Primeiro:

Evaluate
→ Test
→ Compare
→ Decide
→ Implement

---

## 14. Acceptance Criteria

Phase 2.3 será concluída quando:

- fontes gratuitas forem identificadas
- brapi Free for tecnicamente avaliada
- fontes públicas complementares forem identificadas
- gaps forem documentados
- requisitos de opções forem validados
- requisitos PIT forem avaliados
- estratégia de fallback estiver definida
- nenhum provider pago for adotado sem justificativa

---

## 15. Decision

Current decision:

> ADOPT FREE-FIRST STRATEGY.

Initial provider architecture:

> brapi = primary market data development provider
>
> OpLab = primary options data development provider
>
> B3 public data = official validation/reference source
>
> BCB/public data = macro source

This decision is valid for the initial development phase only.

No provider is considered permanently frozen until the integration,
data-quality, coverage, historical and Point-in-Time tests are completed.

No paid provider commitment has been made.

---

## Version

Provider Evaluation: 1.0

Status: READY FOR PHASE 2.4
