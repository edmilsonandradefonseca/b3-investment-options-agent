# B3 Investment \& Options Agent — Sistema Inteligente de Apoio à Decisão para Investimentos na B3



#### Aluno: Edmilson de Andrade Fonseca — [GitHub](https://github.com/edmilsonandradefonseca)

#### Orientadora: Manoela Rabello Kohler



Trabalho apresentado ao curso [BI MASTER](https://ica.puc-rio.ai/bi-master), da Pontifícia Universidade Católica do Rio de Janeiro, como pré-requisito para conclusão de curso e obtenção de crédito na disciplina **Projetos de Sistemas Inteligentes de Apoio à Decisão**.

\---



* \[Link para o código] https://github.com/edmilsonandradefonseca/b3-investment-options-agent

\---



### Resumo



Este trabalho apresenta o desenvolvimento do **B3 Investment \& Options Agent**, uma plataforma de apoio à decisão para investimentos em ações e opções negociadas na B3. O sistema integra informações de mercado, documentos regulatórios, históricos de preços, posições de carteira e operações efetivamente realizadas, com o objetivo de apoiar análises de risco, identificação de oportunidades e comparação de estratégias. A solução combina motores analíticos determinísticos em Python, armazenamento estruturado, busca semântica por embeddings e modelos de linguagem de grande porte (LLMs) usados seletivamente para interpretação de evidências e produção de sínteses. O desenvolvimento seguiu um processo iterativo, no qual restrições de custo, latência, memória, consistência dos dados e confiabilidade das respostas motivaram mudanças arquiteturais: migração de embeddings de 384 para 768 dimensões; evolução do uso do DeepSeek R1 8B para o Qwen3 4B no domínio B3; substituição da orquestração baseada em LLM por fluxos determinísticos em Python; e criação de uma estratégia multifuente de coleta com cache, validação, deduplicação e rastreabilidade. Os resultados documentados demonstram a validação da infraestrutura de inteligência contínua da versão V4.3 e a evolução da V4.4, ainda sujeita a testes e aceites por funcionalidade. Conclui-se que, nesse contexto, sistemas híbridos — com autoridade factual determinística e IA generativa como componente auxiliar — oferecem um caminho mais controlável e auditável do que arquiteturas inteiramente dependentes de LLMs.

**Palavras-chave:** sistemas de apoio à decisão; inteligência artificial; mercado financeiro; opções; RAG; modelos de linguagem; arquitetura híbrida; B3.



### Abstract



This paper presents the development of the **B3 Investment \& Options Agent**, a decision-support platform for equities and options traded on Brazil's B3 exchange. The system combines market information, regulatory disclosures, historical prices, portfolio holdings, and actual trade records to support risk assessment, opportunity screening, and strategy comparison. Its architecture integrates deterministic Python analytics engines, structured storage, semantic retrieval using embeddings, and large language models (LLMs) selectively employed to interpret evidence and generate summaries. Development followed an iterative process shaped by cost, latency, hardware constraints, data consistency, and response reliability. Key architectural changes included migrating from 384- to 768-dimensional embeddings; moving from DeepSeek R1 8B toward Qwen3 4B for the B3 local-analysis workload; replacing LLM-driven task routing with deterministic Python orchestration; and adopting multi-source data acquisition with caching, validation, deduplication, and provenance. Documented outcomes include validation of the V4.3 continuous-intelligence infrastructure, while V4.4 features remain subject to individual integration and acceptance tests. The central finding is that hybrid architectures, where deterministic components retain factual authority and generative AI provides auxiliary interpretation, can improve operational control and auditability compared with fully LLM-dependent approaches.

**Keywords:** decision support systems; artificial intelligence; financial markets; options; retrieval-augmented generation; large language models; hybrid architecture.

\---

### 

### 1\. Introdução



A análise de investimentos em ações e derivativos exige combinar dados de naturezas distintas: preços e volumes de negociação, características dos contratos de opções, demonstrações financeiras, fatos relevantes, notícias, eventos corporativos e informações específicas da carteira do investidor. Esses dados variam em frequência, estrutura, atualidade e confiabilidade. Uma recomendação de venda de uma opção, por exemplo, depende não apenas do prêmio potencial, mas também do preço de exercício, vencimento, liquidez, garantias, risco de exercício, exposição já existente e condições de mercado.

O objetivo deste projeto foi desenvolver um sistema inteligente de **apoio**, e não de execução autônoma, à decisão de investimento. Entre as perguntas que motivaram o projeto estão: *quais posições exigem atenção?*, *vale encerrar ou rolar uma opção vendida?*, *qual estratégia apresenta melhor relação entre capital comprometido e risco?* e *que acontecimentos recentes alteram a tese de investimento de um ativo?*

A hipótese de engenharia explorada foi que uma arquitetura híbrida, combinando modelos de linguagem com regras, cálculos e registros verificáveis, seria mais adequada a esse problema do que delegar todas as etapas a um único LLM. O projeto também adotou a restrição de operar, tanto quanto possível, em infraestrutura local e com baixo custo recorrente.

#### 

#### 1.1 Objetivos



O **objetivo geral** é conceber e implementar uma plataforma modular que transforme dados financeiros heterogêneos em análises contextualizadas, rastreáveis e úteis ao investidor da B3.

Os objetivos específicos são: (i) consolidar carteira e operações de ações e opções; (ii) coletar e qualificar dados de fontes complementares; (iii) calcular exposição, resultados, riscos e cenários com procedimentos determinísticos; (iv) organizar documentos e eventos em memória recuperável; (v) empregar LLMs para interpretação e explicação, sem lhes atribuir autoridade sobre valores financeiros; (vi) disponibilizar os resultados em uma interface compreensível; e (vii) analisar os compromissos entre qualidade, desempenho, custo e robustez.

#### 

#### 1.2 Escopo e limitações



O agente não transmite ordens à corretora e não substitui o julgamento do investidor. A saída consiste em informação, cenários e sugestões condicionadas à qualidade das evidências disponíveis. Nem todas as funções planejadas na versão V4.4 estavam homologadas na data de referência de **8 de outubro de 2026**. Assim, especificação aprovada, teste automatizado, serviço ativo em Ubuntu e aplicativo Windows entregue são estados diferentes, tratados separadamente neste trabalho.

\---

### 

### 2\. Modelagem e arquitetura da solução

#### 

#### 2.1 Arquitetura lógica em sete blocos — organização aprovada



A versão V4.4 foi organizada em **sete blocos de responsabilidade**. A interface React para web/Windows apresenta os resultados de todos os serviços funcionais **por meio do backend FastAPI**: o frontend não consulta diretamente os bancos, os modelos de IA ou os fornecedores de informação financeira. O backend, implementado em Python, roteia solicitações, aciona motores determinísticos e, quando necessário, solicita interpretação a um agente sênior de linguagem. A atualização das bases pode ocorrer sem que a interface esteja aberta.



**Figura 1 — Arquitetura lógica do B3 Agent V4.4 (visão de responsabilidades).** A disposição vertical sintetiza dependências entre componentes; **não** significa que toda consulta percorra os sete blocos em sequência.

|**1. FRONTEND — React / Windows**|
|-|
|**Portfolio · Options · Opportunities · Strategy Lab · Market Intelligence · Copilot**  <br> Interface de apresentação, consulta, gráficos, recomendações, fontes e acompanhamento de tarefas.|

<div align="center">↕ <strong>API REST / WebSocket quando disponível</strong> ↕</div>

|**2. BACKEND — FastAPI + Orquestrador Python**|
|-|
|Validação de solicitações, Fast Router determinístico, contratos de serviço, coordenação de tarefas, status e respostas estruturadas.|

<div align="center">↕ <strong>Acionamento seletivo dos serviços</strong> ↕</div>

|**3. CAMADA DETERMINÍSTICA — Python**|**4. AGENTE SÊNIOR — LLM**|
|-|-|
|Preços, posições, Portfolio, Options, Greeks, payoff, risco, comparação de estratégias e *scoring* de oportunidades.|Análise seletiva de oportunidades e inteligência de mercado, interpretação de conflitos, hipóteses e explicações fundamentadas. **Não substitui os cálculos canônicos.**|

<div align="center">↕ <strong>Consulta a dados e evidências verificáveis</strong> ↕</div>

|**5. CAMADA DE DADOS E CONHECIMENTO**|
|-|
|**SQLite / Parquet / Canonical Evidence**: fatos financeiros, posições, operações e proveniência. <br> **Qdrant (embeddings de 768 dimensões)**: recuperação semântica/RAG. <br> **Neo4j**: grafo de conhecimento e relações entre entidades.|

<div align="center">↑ <strong>Ingestão, indexação e processamento em segundo plano</strong> ↑</div>

|**6. AUTOMAÇÃO — Scheduler e Qwen3 4B**|
|-|
|**Scheduler / systemd**: inicia coleta, reconciliação, atualizações e recuperação de trabalhos. <br> **Qwen3 4B / Ollama**: classifica e sintetiza evidências selecionadas de forma **assíncrona**; seus dossiês só são aproveitados após *quality gate*. <br> **Importante:** o Qwen não opera os conectores nem controla o scheduler.|

<div align="center">↑ <strong>Dados obtidos por conectores Python</strong> ↑</div>

|**7. FONTES DE DADOS**|
|-|
|Yahoo/yfinance · BRAPI · OPLAB · CVM · RI das empresas · B3/COTAHIST · BCB · notícias · extratos BTG · notas de corretagem · arquivos locais.|

*Nota da Figura 1.* Os blocos 3 e 4 são caminhos complementares de análise, e não fases consecutivas obrigatórias. O bloco 5 armazena fatos e projeções de recuperação; os blocos 6 e 7 alimentam esse armazenamento. A solicitação de análise sênior parte do backend apenas quando a tarefa exige interpretação mais complexa. O frontend consome os resultados de todos esses serviços **via FastAPI**.

**Dois fluxos operacionais esclarecem o funcionamento real da arquitetura:**

**Fluxo A — Coleta automática, independente do usuário.**

```text
\\\\\\\[Scheduler / inicialização e recuperação no Ubuntu]
                       |
                       v
\\\\\\\[Conectores Python: Yahoo, CVM, B3, BRAPI, OPLAB, BTG ...]
                       |
                       v
\\\\\\\[Validação, normalização, deduplicação, cache, proveniência]
                       |
                       v
\\\\\\\[SQLite / Parquet / Canonical Evidence]
          |                              |
          v                              v
\\\\\\\[Qdrant 768d / Neo4j]          \\\\\\\[Fila persistente, quando aplicável]
                                         |
                                         v
                              \\\\\\\[Qwen3 4B -> Quality gate]
                                         |
                                         v
                              \\\\\\\[Dossiê derivado opcional]
```

A coleta e a persistência de evidências **não dependem de inferência generativa**. Falhas do Qwen não devem bloquear a entrada de dados admitidos. A atualização do índice vetorial e do grafo não altera a autoridade das bases canônicas.

**Fluxo B — Consulta sob demanda, exemplificada por uma análise de venda de PUT de VALE3.**

```text
\\\\\\\[Usuário no React / Windows]
             |
             v
\\\\\\\[FastAPI + Fast Router Python]
             |
             +----> \\\\\\\[Motores determinísticos + dados canônicos]
             |                    |
             |                    v
             |             \\\\\\\[Cálculos, riscos, cenários]
             |
             +----> \\\\\\\[RAG / Qdrant / Neo4j, quando necessário]
             |
             +----> \\\\\\\[Agente sênior LLM, somente se necessário]
                               ^
                               |
                   \\\\\\\[Dossiê Qwen válido, se disponível]
             |
             v
\\\\\\\[FastAPI: resultados, explicações, fontes e status]
             |
             v
\\\\\\\[Frontend: apresentação -> decisão humana]
```

Nesse exemplo, os motores verificam parâmetros do contrato, prêmio, vencimento, capital necessário, exposição e cenários, conforme os dados efetivamente disponíveis. A análise sênior pode explicar as alternativas e suas incertezas, sem inventar cotações nem sobrepor regras financeiras. O investidor decide; o B3 Agent **não transmite ordens automaticamente**. Para consultas simples, como exibir uma carteira atualizada, o sistema pode responder sem executar Qwen ou agente sênior.

**Limites de implantação.** Este desenho retrata a arquitetura aprovada para V4.4, e não constitui comprovação de que cada componente esteja homologado em produção. Validações de API, tarefas do Ubuntu, integração ponta a ponta e aplicativo desktop Windows exigem evidências próprias.

#### 

#### 2.2 Componentes tecnológicos, responsabilidades e integração



|Camada / componente|Responsabilidade|Relação com o frontend|
|-|-|-|
|**React (web / desktop Windows)**|Exibir carteira, opções, oportunidades, gráficos, simulações, evidências e Copilot; receber comandos e mostrar status de tarefas.|**Cliente de todos os serviços funcionais através da API**, sem lógica financeira duplicada.|
|**FastAPI + Fast Router em Python**|Ponto de entrada REST e, quando suportado, WebSocket; validar pedidos; encaminhar tarefas aos serviços; consultar status e compor respostas.|Contrato único de acesso usado pela interface.|
|**Serviços Python de análise**|Portfolio, Options, Risk, Greeks/payoff, Opportunity scoring, Strategy Lab e Market Intelligence.|A API expõe seus resultados para os workspaces correspondentes e para o Copilot.|
|**Conectores e jobs de coleta**|Obter dados externos e do usuário; tratar datas, consistência, deduplicação, cache e falhas; atualização manual e/ou agendada conforme contrato.|O frontend consulta progresso, última atualização e resultados pela API; não coleta diretamente das fontes.|
|**SQLite / Parquet / Canonical Evidence**|Guardar posições, operações, eventos, estado e fatos identificados com proveniência e point-in-time.|Dados recuperados por serviços e API, nunca acesso direto da interface.|
|**Embeddings 768d + Qdrant**|Indexar conteúdo para recuperação semântica contextual; índices reconstruíveis.|Contexto chega à interface por endpoints e respostas dos serviços.|
|**Neo4j**|Representar vínculos entre empresas, ativos, documentos, eventos e outros relacionamentos relevantes.|Consultado pelo backend; resultados relacionais são expostos pela API.|
|**Ollama / Qwen3 4B**|Análise local curta e assíncrona, produzindo síntese estruturada e opcional, com quality gate.|Estado e dossiês aproveitáveis chegam pelo backend; não é requisito para renderizar resultados determinísticos.|
|**Análise sênior / ferramentas**|Interpretar perguntas abertas, conflitos, hipóteses e análises multi-etapas com dados rastreáveis.|Resposta retornada à API e exibida no workspace ou Copilot.|
|**systemd / scheduler / GitHub Actions**|Operação agendada, recuperação, estados e monitoramento; testes/CI para o ciclo de desenvolvimento.|O frontend pode consultar status operativo, mas não depende de job em execução para abrir.|

A infraestrutura Ubuntu documentada dispõe de aproximadamente **4 núcleos físicos/8 threads, 14,8 GiB de RAM e 4 GiB de swap**. A separação entre requisições rápidas, motores determinísticos, recuperação semântica e inferência em segundo plano foi necessária para adaptar a plataforma a esse limite.

#### 

#### 2.3 Organização funcional e casos de uso atendidos pela API



O frontend, que consome pela API os serviços de análise, as evidências recuperadas, o status de processamento e a síntese sênior quando solicitada, foi organizado em cinco espaços principais: **Portfolio** (posições, custos, proventos e exposição), **Options** (contratos em aberto, prêmios, vencimentos e resultados), **Opportunities** (identificação e avaliação de oportunidades), **Strategy Lab** (comparação de cenários e estratégias) e **Market Intelligence** (indicadores, fundamentos, eventos e contexto de mercado). Um **Copilot** funciona transversalmente como canal de perguntas e explicações. A concepção desses espaços está documentada; o grau de implementação e validação difere entre eles.

#### 

#### 2.4 Dados financeiros e autoridade



A arquitetura estabelece uma distinção essencial entre **fato financeiro** e **interpretação de IA**. Quantidades, posições, preços, prêmios, vencimentos, cálculo de payoff e critérios de risco devem ser produzidos por fontes identificadas e regras reproduzíveis. O LLM pode explicar o significado econômico desses resultados, comparar hipóteses e apontar lacunas, mas não deve inventar cotações, transações ou indicadores ausentes.

O sistema adota, portanto, os princípios de **evidência antes da conclusão**, **proveniência**, **correção temporal (*point-in-time*)** e **UNKNOWN permanece UNKNOWN**. Uma informação ausente não pode ser silenciosamente convertida em zero. Um documento histórico recuperado posteriormente também não deve ser tratado como informação que estava disponível ao investidor em uma data anterior.

#### 

#### 2.5 Desafios técnicos e decisões de engenharia

##### 

##### 2.5.1 Migração dos embeddings: de 384 para 768 dimensões



**Problema.** A primeira configuração de memória semântica utilizava vetores de **384 dimensões**. Ao evoluir a camada de recuperação, adotou-se um serviço de embeddings de **768 dimensões**, atualmente documentado na porta 8093. Índices vetoriais são dependentes da dimensão e do espaço de representação gerado pelo modelo: vetores de tamanhos diferentes não podem ser misturados na mesma coleção configurada para uma dimensão fixa.

**Solução.** A arquitetura passou a utilizar coleções compatíveis com embeddings de 768 dimensões, com reindexação das informações a partir de seus registros originais, preservando os dados canônicos fora do índice vetorial. O Qdrant foi tratado como **projeção reconstruível**, e não como fonte primária da informação. Assim, a troca de modelo de embeddings não exige reescrever as posições, documentos ou registros financeiros originais.

**Aprendizado.** A dimensão do embedding é uma característica estrutural do índice, não uma propriedade isolada do documento. Vetores maiores podem representar informações de maneira diferente, mas **768 dimensões não garantem, por si só, maior precisão**. Para demonstrar ganho de qualidade, é necessário comparar resultados de recuperação em um conjunto comum de consultas, medindo métricas como Recall@k, MRR ou nDCG. Na ausência dessas medições, o resultado comprovável é a migração arquitetural e a compatibilização da indexação — não um ganho quantitativo de precisão.

##### 

##### 2.5.2 Evolução do DeepSeek R1 8B para Qwen3 4B



**Problema.** O **DeepSeek R1 8B** foi utilizado como analista local de evidências na arquitetura V4.3, mas a execução somente em CPU, com memória limitada, introduzia latência, contenção de recursos e risco de respostas incompletas ou truncadas. Em tarefas que precisam de campos estruturados e processamento recorrente, o custo computacional de gerar longas cadeias de raciocínio pode ser inadequado.

**Solução.** A V4.4 passou a especificar o **Qwen3 4B quantizado em Q4\_K\_M**, em modo *non-thinking*, para tarefas mais restritas de classificação, extração e síntese estruturada. O formato JSON é submetido a validação (*quality gate*), e o processamento ocorre em filas assíncronas. Um resultado inválido, incompleto ou desatualizado não adquire status de fato financeiro e pode ser descartado ou reprocessado. A mudança se refere ao **trabalho local do domínio B3**: o documento consolidado não comprova que o modelo ativo do projeto separado João Resolve tenha sido integralmente migrado.

**Aprendizado.** Um modelo menor, usado em uma tarefa estreitamente definida, pode ser arquiteturalmente mais adequado do que um modelo maior responsável por etapas demais. A conclusão não é que Qwen seja universalmente superior a DeepSeek, mas que a arquitetura buscou reduzir a demanda computacional e aumentar o controle dos contratos de saída. Uma comparação quantitativa definitiva de tempo, memória, taxa de JSON válido e qualidade das respostas ainda depende de benchmark controlado.

##### 

##### 2.5.3 Da orquestração por LLM ao processamento determinístico em Python



**Problema.** Uma hipótese inicial consistia em empregar DeepSeek ou Qwen como orquestrador central: interpretar cada solicitação, decidir qual ferramenta executar e comandar a sequência completa. Essa abordagem introduzia chamadas generativas mesmo em tarefas previsíveis, aumentando o tempo de resposta e tornando o fluxo operacional dependente da disponibilidade da inferência local.

**Solução.** Foi desenvolvido um **roteador determinístico em Python**, que identifica contratos conhecidos e encaminha diretamente para os motores especializados. Tarefas de coleta, cálculo, atualização de status e processamento em lote são executadas sem passar obrigatoriamente por um LLM. O raciocínio generativo fica reservado para interpretação de situações complexas, explicações e tarefas ambíguas. A análise local é paralela e opcional, não parte obrigatória do caminho crítico.

**Aprendizado.** O LLM deve ser empregado onde há ambiguidade semântica, interpretação ou síntese; regras de negócio, identificação de comandos tipados, cálculos e estados de execução são mais previsíveis quando expressos em código. Essa decisão também facilita testes automatizados, rastreamento de erros, controle de tempo de execução e reprodução dos resultados.

##### 

##### 2.5.4 Coleta multifuente: custo, cobertura e confiabilidade



**Problema.** Nenhuma fonte isolada atendia, simultaneamente, a todos os requisitos de histórico, cotação, opções, dados corporativos, proventos e operações reais da carteira. Fontes gratuitas podem apresentar lacunas ou diferenças de ajuste e atualização; APIs especializadas podem impor franquias, autenticação, instabilidade temporária ou indisponibilidade de campos.

**Solução.** Adotou-se uma arquitetura de provedores complementares, com **prioridade por tipo de informação**. Para preços e histórico: reutilização de cache previamente validado e consulta a Yahoo/yfinance, com OPLAB e BRAPI como alternativas segundo capacidade e disponibilidade. Para cadeias de opções, a fonte prioritária é a **OPLAB**, com verificação de código, strike, vencimento, bid/ask e liquidez. Para fatos societários, documentos e validação oficial: **CVM, relações com investidores e B3**. Para dados macroeconômicos: **Banco Central**. Para histórico offline: **COTAHIST**. Para posições e prêmios de execução reais: **extratos BTG e notas de corretagem**.

A coleta é acompanhada de normalização de campos, datas e fusos, cache, validações, deduplicação e registro de proveniência. A fonte e a data da informação devem acompanhar a conclusão. Na V4.4, o limite conhecido de **15.000 chamadas mensais da BRAPI** motivou a especificação de controle persistente de consumo; o documento de arquitetura, entretanto, não atesta que todos os mecanismos de controle da franquia já estivessem implementados.

**Aprendizado.** Reduzir custos de dados não é simplesmente escolher uma API gratuita. É necessário reduzir chamadas redundantes, reaproveitar histórico validado, selecionar a fonte adequada a cada campo e impedir que divergências silenciosas contaminem a análise. A estratégia multifuente aumenta a resiliência, mas também exige regras claras de precedência e resolução de conflitos.

##### 

##### 2.5.5 Execução assíncrona e limitação de recursos



**Problema.** Serviços de API, persistência, indexação e inferência competem pelos mesmos recursos do Ubuntu. Um processo de inferência pesado pode aumentar a latência e comprometer tarefas essenciais. Além disso, timeouts de provedores ou reinicializações do host não devem provocar perda de dados ou reprocessamento sem controle.

**Solução.** A arquitetura separou o caminho determinístico das filas de inferência local. Na V4.3 foi estabelecido um **lock físico compartilhado** (`/var/lock/local-reasoning.lock`) para limitar inferências pesadas concorrentes. Em caso de contenção, o trabalho pode ser adiado e reenfileirado, preservando a evidência já adquirida. O pipeline de inteligência contínua emprega cursor persistente com janela de sobreposição (*overlap*) e identificadores de deduplicação. A V4.4 também prevê recuperação incremental ao ligar o servidor, em vez de depender exclusivamente de operação noturna ininterrupta; a migração completa de todos os timers para essa política ainda requer verificação operacional.

**Aprendizado.** Processos longos devem ter estados observáveis, persistência e possibilidade de retomada. A indisponibilidade temporária do LLM não pode bloquear cálculos ou invalidar fatos previamente obtidos.

##### 

##### 2.5.6 Qualidade da informação, rastreabilidade e risco de alucinação



**Problema.** Uma resposta textual convincente pode conter preços inexistentes, conclusões baseadas em informação antiga ou relações causais não sustentadas pelos documentos. Em investimentos, esse tipo de erro pode produzir decisões materialmente equivocadas.

**Solução.** Implementou-se a separação entre **Evidence canônico** e **inteligência derivada**. Documentos são identificados por fonte, emissor, instante de referência e identidade; a avaliação de materialidade é determinística. O LLM produz dossiês auxiliares que passam por validação, com estados como READY, DEGRADED ou DEFERRED. Resultados inadequados não são promovidos automaticamente ao contexto sênior. A decisão final sobre comprar, vender, exercer ou rolar posições permanece humana.

**Aprendizado.** Rastreabilidade, detecção de ausência de dados e governança de autoridade são tão importantes quanto a fluência de um modelo generativo. No domínio financeiro, uma afirmação não verificada deve permanecer incerta.

\---

### 

### 3\. Resultados e avaliação



O projeto obteve como principal resultado de engenharia uma **arquitetura modular de apoio à decisão**, com a interface React desacoplada da execução e consumindo os serviços do backend FastAPI. A solução combina diferentes tipos de evidência sem delegar a um modelo de linguagem o controle absoluto dos fatos financeiros ou do fluxo de execução.

#### 

#### 3.1 Resultados documentados e validados



A documentação de congelamento da V4.3 registra o pipeline **Continuous Intelligence** com descoberta incremental de documentos da CVM, cursor persistente, deduplicação, Evidence canônico, triagem determinística, fila de relevância, geração de dossiês derivados e observabilidade. O relatório de aceite registra verificações com status **PASS** para componentes da infraestrutura contínua, timers, descoberta, API de observabilidade, lock de inferência compartilhado, identidade de emissores e disponibilidade do backend. No checkpoint documentado, a integração contínua registrou **623 testes Python e testes React aprovados**. Esses números constituem evidência histórica da versão e do escopo testados; não garantem, sem nova execução, o comportamento de mudanças posteriores.

Também foi implementada uma política arquitetural de **não negociação autônoma**: o agente apresenta análises e cenários, mas a autorização e eventual execução de ordens permanecem fora de sua autoridade.

#### 

#### 3.2 Evolução da V4.4 e resultados ainda em validação



A V4.4 introduziu o Qwen3 4B como referência para o processamento local do B3, redefiniu prioridades de fontes de dados e formalizou a experiência de cinco workspaces em React, com aplicativo Windows como alvo de distribuição. O documento consolidado registra código e testes associados à evolução, porém destaca a necessidade de confirmar versão efetivamente instalada, qualidade ponta a ponta das respostas, cobertura das fontes, consumo de APIs e funcionamento de todos os recursos em produção.

Os espaços **Opportunities, Strategy Lab e Market Intelligence** apresentavam implementações e validações parciais. O instalador Windows independente também dependia de aceite específico. Por isso, a avaliação final distingue a **infraestrutura V4.3 validada** da **experiência V4.4 em evolução**.

#### 

#### 3.3 Critérios propostos para avaliação quantitativa



A análise qualitativa das decisões arquiteturais deve ser complementada, antes da entrega acadêmica definitiva, com medições reproduzíveis:

|Questão avaliada|Indicador recomendado|Método|
|-|-|-|
|Qualidade da busca semântica|Recall@5, MRR e nDCG@10|Mesmo conjunto de perguntas e documentos, comparando os índices 384d e 768d.|
|Desempenho da inferência|Latência p50/p95, memória máxima, taxa de JSON válido|Mesmo lote de evidências, executado em condições controladas com DeepSeek 8B e Qwen 4B.|
|Benefício da orquestração Python|Tempo total por tarefa, número de chamadas LLM e taxa de falhas|Comparação entre roteamento generativo e determinístico.|
|Eficiência da aquisição de dados|Chamadas por provedor, taxa de cache e cobertura informacional|Telemetria por fonte e por tipo de dado.|
|Confiabilidade da coleta|Cobertura dos campos, erros, divergências e reutilização de cache|Amostragem de ações, opções e datas.|
|Qualidade das análises financeiras|Exatidão de cálculos, rastreabilidade e casos com UNKNOWN|Cenários de referência validados manualmente.|

**Nota metodológica:** esses indicadores são propostas de avaliação; não se apresentam valores experimentais inexistentes. A tese deve registrar parâmetros, hardware, conjunto de teste, versões, datas e resultados brutos sempre que houver medição.

\---

### 

### 4\. Conclusões



O desenvolvimento do B3 Investment \& Options Agent evidenciou que a principal dificuldade de um sistema inteligente de apoio à decisão financeira não é simplesmente integrar um modelo de linguagem, mas construir uma infraestrutura que produza **informações confiáveis, cálculos reproduzíveis, respostas oportunas e recomendações rastreáveis**, dentro de limites de custo e capacidade computacional.

As alterações realizadas durante o projeto ilustram essa conclusão. A migração dos embeddings de 384 para 768 dimensões reforçou a necessidade de desacoplar a memória semântica dos registros canônicos. A evolução do DeepSeek R1 8B para o Qwen3 4B evidenciou a importância de adequar o modelo à tarefa e ao hardware disponível. A substituição da orquestração generativa pelo roteamento em Python eliminou a dependência de inferência para operações determinísticas. A estratégia multifuente de coleta demonstrou que custo, disponibilidade e confiabilidade precisam ser tratados em conjunto.

A contribuição central do projeto está, portanto, na **separação entre quatro responsabilidades**: os provedores e registros canônicos fornecem os fatos; os motores determinísticos executam cálculos e políticas de negócio; os LLMs interpretam evidências e ajudam a explicar alternativas; e a interface consome, via API, todos esses serviços e apresenta seus resultados ao investidor. Essa separação reduz o risco de que uma resposta generativa seja confundida com uma cotação, posição ou decisão executável.

Como limitações, destacam-se a necessidade de benchmarks comparativos entre modelos e embeddings, a mensuração da eficiência da coleta financeira, a validação completa dos workspaces da V4.4, a verificação de coleta e análise após reinício do servidor e o aceite do aplicativo desktop. Também permanecem relevantes testes em diferentes regimes de mercado, comparação com análises independentes e estudo sistemático da qualidade das recomendações geradas.

Conclui-se que o B3 Agent constitui um estudo de caso de **engenharia de sistemas inteligentes híbridos**, no qual mudanças motivadas por problemas reais de desempenho, custo e qualidade produziram uma arquitetura mais modular, observável e auditável. O agente permanece uma ferramenta de apoio: a decisão de investimento é sempre humana.

\---

### 

### Referências técnicas e documentação do projeto

* [Repositório B3 Investment \& Options Agent](https://github.com/edmilsonandradefonseca/b3-investment-options-agent)
* [Arquitetura B3 V4.4](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/blob/main/docs/ARCHITECTURE_V4.4.md)
* [Especificação dos workspaces V1.2](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/blob/main/docs/FRONTEND_DECISION_WORKSPACES_SPEC_V1.2.md)
* [PR #66 — evolução de integração](https://github.com/edmilsonandradefonseca/b3-investment-options-agent/pull/66)
* **Documento de apoio:** *Arquitetura Consolidada João Resolve + B3 Investment \& Options Agent*, V4.4, revisão de 08/10/2026 (documento fornecido pelo autor). As seções 18–25 atualizam as decisões anteriores da V4.3.

\---

Pontifícia Universidade Católica do Rio de Janeiro  
Curso de Pós-Graduação *Business Intelligence Master*

