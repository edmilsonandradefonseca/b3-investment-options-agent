export type PageId =
  | "Overview"
  | "Portfolio"
  | "Options"
  | "Opportunities"
  | "Market Regime"
  | "Experience & Learning"
  | "Historical Similarity"
  | "Risk & Stress"
  | "Copilot";

export type PageDefinition = {
  id: PageId;
  route: string;
  icon: string;
  subtitle: string;
  prompt: string;
  description: string;
};

export const PAGE_DEFINITIONS: PageDefinition[] = [
  {
    id: "Overview",
    route: "overview",
    icon: "⌂",
    subtitle: "Visão consolidada V4",
    prompt: "Resuma o estado atual do portfólio, mercado, riscos e principais mudanças.",
    description: "Resumo executivo sem inventar dados ausentes.",
  },
  {
    id: "Portfolio",
    route: "portfolio",
    icon: "◫",
    subtitle: "Posições e exposição",
    prompt: "Analise a composição, concentração, capital e exposições do meu portfólio.",
    description: "Fonte: PortfolioContext e engines determinísticos.",
  },
  {
    id: "Options",
    route: "options",
    icon: "◈",
    subtitle: "Lifecycle e estruturas",
    prompt: "Analise minhas posições e operações de opções atuais, incluindo lifecycle e riscos.",
    description: "Posições, obrigações, assignment e estruturas.",
  },
  {
    id: "Opportunities",
    route: "opportunities",
    icon: "◎",
    subtitle: "Ranking + contexto",
    prompt: "Quais oportunidades atuais são elegíveis e como a experiência histórica as contextualiza?",
    description: "Score determinístico separado de ExperienceAssessment.",
  },
  {
    id: "Market Regime",
    route: "market-regime",
    icon: "◌",
    subtitle: "Regime e fatores",
    prompt: "Qual é o regime de mercado atual e quais fatores o suportam?",
    description: "Classificação reproduzível e versionada.",
  },
  {
    id: "Experience & Learning",
    route: "experience-learning",
    icon: "◇",
    subtitle: "Aprendizados e drift",
    prompt: "Quais aprendizados ativos, enfraquecendo ou em drift são relevantes agora?",
    description: "Evidências, confiança, aging, contradição e drift.",
  },
  {
    id: "Historical Similarity",
    route: "historical-similarity",
    icon: "≈",
    subtitle: "Precedentes similares",
    prompt: "Quais experiências históricas são mais similares ao contexto atual e por quê?",
    description: "Feature similarity + regime + aging + semântica.",
  },
  {
    id: "Risk & Stress",
    route: "risk-stress",
    icon: "△",
    subtitle: "Cenários e stress",
    prompt: "Mostre os principais riscos e cenários de stress relevantes para a carteira atual.",
    description: "ScenarioDefinition → StressResult, sem previsão implícita.",
  },
  {
    id: "Copilot",
    route: "copilot",
    icon: "✦",
    subtitle: "Racional conversacional",
    prompt: "Explique o racional consolidado para o contexto atual, com evidências e limitações.",
    description: "Síntese contextual; decisão final continua humana.",
  },
];

export function pageFromHash(hash = window.location.hash): PageId {
  const route = hash.replace(/^#\/?/, "").trim();
  return PAGE_DEFINITIONS.find((page) => page.route === route)?.id ?? "Overview";
}

export function hashForPage(pageId: PageId): string {
  const page = PAGE_DEFINITIONS.find((item) => item.id === pageId);
  return `#/${page?.route ?? "overview"}`;
}

export function getPageDefinition(pageId: PageId): PageDefinition {
  return PAGE_DEFINITIONS.find((item) => item.id === pageId) ?? PAGE_DEFINITIONS[0];
}
