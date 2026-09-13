# Data Provider Strategy v1

## 1. Objetivo

Definir a estratégia de aquisição de dados do B3 Investment & Options Agent,
mantendo o núcleo do sistema independente de qualquer provedor externo.

Arquitetura:

Provider
→ Adapter
→ Data Contract
→ Point-in-Time Validation
→ Storage
→ Analytical Engines

Nenhum componente de negócio deve depender diretamente de uma API externa.

---

## 2. Princípios

1. Provider independence
2. Point-in-Time correctness
3. Reprodutibilidade
4. Provenance
5. Data quality
6. Fail-safe behavior
7. Substituibilidade de provedores
8. Separação RAW / NORMALIZED / DERIVED
9. Nenhum dado externo deve alterar diretamente uma decisão de investimento
10. Nenhuma integração real nesta fase

---

## 3. Data Domains

### 3.1 Instrument Reference

Dados necessários:

- ticker
- instrument_id
- nome
- tipo de ativo
- bolsa
- moeda
- setor
- indústria
- período de atividade

Prioridade: CRITICAL

---

### 3.2 Stock Market Data

Dados necessários:

- OHLC
- volume
- VWAP quando disponível
- timestamp de observação
- timestamp de disponibilidade
- corporate actions para ajuste quando aplicável

Prioridade: CRITICAL

---

### 3.3 Fundamentals

Dados necessários:

- receita
- EBITDA
- EBIT
- lucro líquido
- fluxo de caixa
- dívida
- caixa
- patrimônio líquido
- ativos
- passivos
- métricas por ação
- indicadores de rentabilidade
- períodos contábeis
- data de publicação/disponibilidade

Prioridade: CRITICAL

---

### 3.4 Corporate Actions

Dados necessários:

- dividendos
- JCP
- splits
- grupamentos
- bonificações
- subscrições
- outros eventos relevantes

Prioridade: CRITICAL

---

### 3.5 Options

Dados necessários:

- option_id
- ticker da opção
- ativo subjacente
- tipo PUT/CALL
- strike
- vencimento
- bid
- ask
- last
- volume
- open interest
- implied volatility
- Greeks quando disponíveis
- contract multiplier
- timestamp

Prioridade: CRITICAL

---

### 3.6 Macro

Dados desejáveis:

- SELIC
- IPCA
- CDI
- câmbio
- juros futuros
- indicadores macroeconômicos relevantes

Prioridade: HIGH

---

### 3.7 News

News não faz parte do Data Contract v1.

Será especificada posteriormente.

---

## 4. Provider Tiers

### Tier 1 — Primary Provider

Fonte preferencial para cada domínio.

Características:

- qualidade
- estabilidade
- cobertura
- histórico
- timestamp confiável
- licença compatível
- custo aceitável

---

### Tier 2 — Secondary Provider

Fonte alternativa utilizada para:

- validação
- fallback
- gaps
- comparação de qualidade

---

### Tier 3 — Public / Experimental

Fontes utilizadas somente para:

- prototipagem
- desenvolvimento
- testes
- exploração

Não devem ser consideradas automaticamente fonte de produção.

---

## 5. Adapter Interface

Cada provider deverá implementar uma interface interna comum.

Responsabilidades do Adapter:

- autenticação
- comunicação com provider
- paginação
- rate limits
- retries
- tratamento de erros
- conversão para Data Contract
- preservação de provenance
- normalização de timestamps

O Adapter NÃO deve:

- calcular indicadores de investimento
- fazer valuation
- gerar recomendações
- tomar decisões
- chamar o LLM

---

## 6. Provider Registry

O sistema deverá possuir um registro lógico de providers por domínio.

Exemplo:

instrument → provider
market → provider
fundamental → provider
corporate_action → provider
options → provider
macro → provider

O restante do sistema não deve conhecer detalhes do provider.

---

## 7. Data Quality

Cada ingestão deve permitir classificar os dados como:

- VALID
- WARNING
- INVALID
- MISSING
- STALE
- SUSPECT

Quality flags devem registrar problemas específicos.

Exemplos:

- missing_field
- invalid_timestamp
- duplicate_record
- stale_data
- inconsistent_price
- inconsistent_volume
- provider_error
- incomplete_option_chain

---

## 8. Point-in-Time

Todo dado utilizado em uma decisão histórica deve obedecer:

available_timestamp <= decision_timestamp

Nunca utilizar:

- resultado financeiro ainda não publicado
- preço futuro
- corporate action ainda desconhecida
- opção ainda não existente
- informação revisada posteriormente sem controle de versão

---

## 9. RAW Layer

Dados RAW devem ser:

- imutáveis
- armazenados com provenance
- associados ao provider
- associados ao timestamp de ingestão
- preservados para auditoria

RAW não deve ser sobrescrito.

---

## 10. NORMALIZED Layer

A camada NORMALIZED converte diferentes providers para os Data Contracts internos.

Exemplo:

Provider A
→ Adapter A
→ StockMarketData

Provider B
→ Adapter B
→ StockMarketData

O Analytical Engine recebe somente:

StockMarketData

e não conhece A ou B.

---

## 11. DERIVED Layer

Indicadores derivados pertencem ao Analytical Layer.

Exemplos:

- SMA
- EMA
- RSI
- MACD
- ATR
- volatility
- valuation ratios
- fair value
- margin of safety
- option yield
- probability metrics
- PUT score
- CALL score

Esses dados não devem ser confundidos com dados RAW do provider.

---

## 12. Failure Policy

Se o provider primário falhar:

1. registrar erro
2. não produzir dados silenciosamente incompletos
3. tentar provider secundário quando configurado
4. marcar provenance
5. registrar quality flags
6. impedir decisão quando os dados críticos forem insuficientes

O sistema deve preferir:

WAIT

a produzir uma decisão baseada em dados suspeitos ou incompletos.

---

## 13. Provider Selection Criteria

Cada provider será avaliado por:

- cobertura B3
- cobertura histórica
- qualidade OHLC
- qualidade de volume
- fundamentos
- corporate actions
- opções
- timestamps
- Point-in-Time capability
- estabilidade
- rate limits
- custo
- licença
- facilidade de integração
- confiabilidade

---

## 14. Provider Evaluation

Antes de integrar um provider real, será criada uma avaliação contendo:

- provider
- domínio
- cobertura
- qualidade
- histórico
- PIT capability
- custo
- limitações
- riscos
- fallback
- decisão

Nenhum provider será adotado apenas por conveniência de API.

---

## 15. Storage

RAW:

Parquet / arquivo imutável.

NORMALIZED:

Parquet.

Operational / decisions:

SQLite.

Analytical datasets:

Parquet.

---

## 16. Secrets

Credenciais nunca devem ser:

- armazenadas no código
- commitadas no Git
- colocadas em documentação
- armazenadas em arquivos versionados

Credenciais deverão utilizar environment variables ou secret manager apropriado.

---

## 17. Scope of Phase 2.2

Nesta fase NÃO será implementado:

- API real
- autenticação real
- download de dados B3
- scraping
- broker integration
- trading execution

Será implementada somente a estratégia e a interface necessária para permitir futuras integrações.

---

## 18. Acceptance Criteria

Phase 2.2 será considerada concluída quando:

- estratégia de providers estiver documentada
- responsabilidades do Adapter estiverem definidas
- fallback estiver definido
- Data Quality estiver definido
- PIT estiver preservado
- RAW/NORMALIZED/DERIVED estiver definido
- secrets policy estiver definida
- nenhuma dependência direta de provider existir no core
- testes básicos da interface estiverem implementados

---

## 19. Version

Data Provider Strategy Version: 1.0

Status: DRAFT

