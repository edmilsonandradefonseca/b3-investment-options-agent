export type PageId =
  | "Overview"
  | "Portfolio"
  | "Options"
  | "Opportunities"
  | "Strategy Lab"
  | "Market Intelligence"
  | "History & Learning"
  | "Risk & Stress"
  | "Copilot";

export type PageTab = {
  id: string;
  label: string;
  useCases: string[];
  prompt: string;
  description: string;
};

export type PageDefinition = {
  id: PageId;
  route: string;
  icon: string;
  subtitle: string;
  useCases: string[];
  prompt: string;
  description: string;
  tabs?: PageTab[];
};

export const PAGE_DEFINITIONS: PageDefinition[] = [
  {
    id: "Overview",
    route: "overview",
    icon: "⌂",
    subtitle: "Visão consolidada",
    useCases: ["UC-01", "UC-02", "UC-03", "UC-05", "UC-08", "UC-11"],
    prompt: "Resuma o estado atual do portfólio, opções, oportunidades, mercado, aprendizados e riscos. Preserve as_of, qualidade, limitações e fontes.",
    description: "Resumo executivo do runtime canônico.",
  },
  {
    id: "Portfolio",
    route: "portfolio",
    icon: "◫",
    subtitle: "Posições e exposição",
    useCases: ["UC-01"],
    prompt: "UC-01 Portfolio Intelligence: apresente posições, custo médio, preço atual, valor de mercado, P&L, concentração, capital disponível/UNKNOWN, capital comprometido, obrigações de opções, riscos e provenance.",
    description: "UC-01 · Carteira, capital, concentração e risco.",
  },
  {
    id: "Options",
    route: "options",
    icon: "◈",
    subtitle: "Lifecycle e estruturas",
    useCases: ["UC-02"],
    prompt: "UC-02 Options Position & Lifecycle Intelligence: apresente posições de opções, underlying, strike, vencimento, DTE, prêmio, preço, IV/Greeks quando disponíveis, moneyness, cobertura, assignment/exercise exposure, P&L e alternativas canônicas.",
    description: "UC-02 · PUT/CALL, lifecycle, coverage e assignment.",
  },
  {
    id: "Opportunities",
    route: "opportunities",
    icon: "◎",
    subtitle: "Ranking + contexto",
    useCases: ["UC-03"],
    prompt: "UC-03 Opportunity Discovery: retorne somente oportunidades do pipeline canônico, com ranking, score determinístico e componentes, capital necessário, liquidez, risco, impacto na carteira, experiência histórica, evidências, quality e as_of.",
    description: "UC-03 · Oportunidades canônicas, filtros e evidências.",
  },
  {
    id: "Strategy Lab",
    route: "strategy-lab",
    icon: "⇄",
    subtitle: "Comparação e what-if",
    useCases: ["UC-04"],
    prompt: "UC-04 Strategy Comparison & What-if: compare as alternativas canônicas disponíveis usando os mesmos fatos, mostrando capital, payoff, risco, impacto na carteira, oportunidade, histórico, assumptions e limitações. Separe fatos de hipóteses.",
    description: "UC-04 · Comparação determinística de estratégias.",
  },
  {
    id: "Market Intelligence",
    route: "market-intelligence",
    icon: "◌",
    subtitle: "Regime, fatores e eventos",
    useCases: ["UC-05", "UC-06", "UC-10"],
    prompt: "UC-05 Market & Regime Intelligence: descreva o regime atual com trend, volatilidade, rates, FX, commodities, flow e eventos, preservando as_of e provenance.",
    description: "UC-05/06/10 · Contexto de mercado e evidências.",
    tabs: [
      {
        id: "regime",
        label: "Regime",
        useCases: ["UC-05"],
        prompt: "UC-05 Market & Regime Intelligence: apresente regime, dimensões, tendência, volatilidade, drawdown, taxas, FX, commodities, fluxo, eventos, qualidade, as_of e fontes.",
        description: "Regime reproduzível e point-in-time.",
      },
      {
        id: "factors",
        label: "Factors",
        useCases: ["UC-06"],
        prompt: "UC-06 Contextual Factor Intelligence: apresente estudos de fatores disponíveis, métricas de associação, effect size quando disponível, sample size, multiple-testing safeguards, holdout/walk-forward stability, status e limitações. Associação não é causalidade. Se histórico for insuficiente, retorne LIMITED explicitamente.",
        description: "Fatores validados e estabilidade estatística.",
      },
      {
        id: "research",
        label: "Research & Events",
        useCases: ["UC-10"],
        prompt: "UC-10 Research, News & Event Intelligence: apresente eventos e evidências PIT-safe, publication time, source refs, ativos/posições/learnings afetados e classificação support/contradict/update/no-material-impact.",
        description: "Notícias e eventos transformados em evidência.",
      },
    ],
  },
  {
    id: "History & Learning",
    route: "history-learning",
    icon: "◇",
    subtitle: "Operações, learnings e precedentes",
    useCases: ["UC-07", "UC-08", "UC-09"],
    prompt: "UC-08 Experience & Continuous Learning: apresente learnings, lifecycle, confiança, amostra, evidências favoráveis/contrárias, recent vs long-term, drift, regime, last confirmation e provenance.",
    description: "UC-07/08/09 · Experiência histórica e aprendizado.",
    tabs: [
      {
        id: "operations",
        label: "Operations",
        useCases: ["UC-07"],
        prompt: "UC-07 Historical Operation Reconstruction: apresente operações reconstruídas com source transactions, entry/during/exit feature snapshots, outcome, PIT provenance e campos ausentes. Se outcomes não existirem, mostre isso explicitamente.",
        description: "Reconstrução point-in-time das operações.",
      },
      {
        id: "learnings",
        label: "Learnings",
        useCases: ["UC-08"],
        prompt: "UC-08 Experience & Continuous Learning: apresente learning lifecycle, confidence, sample size, supporting/contradicting evidence, long-term vs recent performance, drift, validity, last confirmation e versions. Se insuficiente, retorne LIMITED.",
        description: "Learnings persistentes, drift e contradições.",
      },
      {
        id: "similarity",
        label: "Similarity",
        useCases: ["UC-09"],
        prompt: "UC-09 Historical Similarity & Precedent Retrieval: apresente precedentes ranqueados com feature similarity, regime similarity, semantic relevance, temporal relevance, evidence quality, outcomes e diferenças relevantes. Se corpus real for insuficiente, retorne LIMITED.",
        description: "Precedentes similares explicáveis.",
      },
    ],
  },
  {
    id: "Risk & Stress",
    route: "risk-stress",
    icon: "△",
    subtitle: "Cenários e stress",
    useCases: ["UC-11"],
    prompt: "UC-11 Risk, Scenario & Stress Intelligence: apresente cenários canônicos disponíveis, assumptions, impacto P&L da carteira e posições, option/assignment exposure, capital requirement, concentração, liquidez, sensitivities e validation status.",
    description: "UC-11 · Stress determinístico e sensitivities.",
  },
  {
    id: "Copilot",
    route: "copilot",
    icon: "✦",
    subtitle: "Racional e decisão humana",
    useCases: ["UC-12"],
    prompt: "UC-12 Decision Rationale & Conversational Copilot: sintetize fatos determinísticos, regime, carteira, opções, precedentes, learnings, evidências favoráveis/contrárias, riscos, incertezas, dados faltantes, sources e as_of. Não execute nem proponha controles de ordens.",
    description: "UC-12 · Síntese explicável sobre o runtime.",
  },
];

export function pageFromHash(hash = window.location.hash): PageId {
  const route = hash.replace(/^#\/?/, "").split("?")[0].trim();
  return PAGE_DEFINITIONS.find((page) => page.route === route)?.id ?? "Portfolio";
}

export function hashForPage(pageId: PageId): string {
  const page = PAGE_DEFINITIONS.find((item) => item.id === pageId);
  return `#/${page?.route ?? "portfolio"}`;
}

export function getPageDefinition(pageId: PageId): PageDefinition {
  return PAGE_DEFINITIONS.find((item) => item.id === pageId) ?? PAGE_DEFINITIONS[0];
}
