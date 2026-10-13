from __future__ import annotations

import json
from typing import Any

from b3_agent.agents.context import AgentContext
from b3_agent.llm.client import LLMClient


_SPECIALIST_KEYS = (
    "market_agent_analysis",
    "portfolio_agent_analysis",
    "options_agent_analysis",
)


class SynthesisAgent:
    """Reconciles independent specialist analyses into a decision-ready context.

    The synthesis layer does not calculate, rank opportunities, fetch provider data,
    or execute trades. It makes conflicts and uncertainty explicit for the existing
    deterministic risk gate and decision schema.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def synthesize(self, context: AgentContext | dict[str, Any]) -> dict[str, Any]:
        payload = context.to_payload() if isinstance(context, AgentContext) else context
        facts = payload.get("deterministic_context", {})
        if not isinstance(facts, dict):
            facts = {}
        deterministic_facts = {
            key: value for key, value in facts.items() if key not in _SPECIALIST_KEYS
        }
        specialist_outputs = {
            key: facts[key] for key in _SPECIALIST_KEYS if key in facts
        }
        result = self.llm.complete_json(
            instructions=(
                "Atue como a camada de síntese do copiloto de decisões de investimento. Produza uma leitura integrada, "
                "curta e útil do pedido usando todos os fatos canônicos, análises dos especialistas, pesquisa recuperada e "
                "inteligência derivada realmente fornecidos. Não invente dados, datas ou fontes; não faça cálculos novos, "
                "não reordene oportunidades e não execute operações.\n\n"
                "PAPÉIS E AUTORIDADE: os serviços determinísticos B3 são a fonte de verdade para preços, séries históricas, "
                "indicadores técnicos, métricas fundamentais, posições/quantidades/contratos, cotações de opções, custos, "
                "exposição e cálculos de risco. Ao usar esses dados, preserve valor, unidade, ativo e data/hora. João Resolve "
                "e a pesquisa interpretam contexto, notícias, eventos e possíveis fatores causais; atribua cada afirmação à "
                "fonte e à data disponíveis. João, memória, pesquisa e agentes não corrigem nem substituem fatos B3. Use "
                "histórico pessoal apenas quando houver execuções/outcomes pertinentes e identifique o período/amostra; "
                "não converta amostra vazia ou não elegível em ausência de risco ou probabilidade.\n\n"
                "SÍNTESE DA DECISÃO: comece pelo que os dados indicam fazer agora (manter/aguardar/aumentar/reduzir ou "
                "alternativa condicional), sem contradizer a proposta nem o gate determinístico. Explique em linguagem "
                "simples por que, usando as evidências que realmente mudam a decisão. Para leitura técnica, interprete os "
                "valores fornecidos de preço versus médias, RSI, MACD, volatilidade e drawdown por horizonte; dê os números "
                "e a data quando disponíveis e esclareça que são observações históricas, não previsões. Para fundamentos, "
                "diga o que as métricas fornecidas sugerem e suas limitações; não chame uma ação de barata/cara sem valuation "
                "qualificado. Para notícias/eventos, resuma somente itens elegíveis no corte, com data/fonte e implicação "
                "plausível; diferencie fato observado de interpretação. Integre concentração, ações, opções vendidas/compradas, "
                "caixa conhecido/desconhecido e histórico pessoal à consequência da decisão quando constarem do contexto.\n\n"
                "FORMATO E QUALIDADE: responda em português claro do Brasil. summary: no máximo 3 frases curtas e 65 palavras; "
                "comece exatamente com 'Leitura prática:' e declare ação/leitura, motivo principal e dado concreto que poderia "
                "mudar a decisão. agreements: poucos achados convergentes com valores/datas e efeito prático. conflicts: "
                "aponte fontes, valores, datas e efeito somente quando fornecidos; se unidades ou datas impedem conciliação, "
                "diga isso sem calcular diferença. uncertainties: condições futuras não confirmadas. evidence_gaps: nomeie "
                "o dado específico ausente, por que importa e que conclusão/operação ele impede. evidence_refs: use apenas "
                "referências fornecidas. Compare explicitamente cada alternativa recebida e diga sua consequência; não "
                "despeje tabelas diagnósticas nem listas repetidas. Se cobertura da busca estiver incompleta, não diga que "
                "não há notícias; explique o limite. 'VALIDATED' ou 'PASS' descreve somente a validação recebida, não prova "
                "que as fontes cobrem todos os dados. Explique termos técnicos na primeira ocorrência; por exemplo, valuation "
                "é estimativa de valor justo e cadeia executável de opções exige cotações atuais de compra/venda, liquidez e "
                "detalhes do contrato. Não substitua análise por ressalvas genéricas nem apresente ordem técnica adiada como "
                "ranking econômico."
            ),
            input_text=json.dumps(
                {
                    "request": payload.get("request"),
                    "deterministic_facts": deterministic_facts,
                    "specialist_analyses": specialist_outputs,
                    "retrieved_evidence": payload.get("retrieved_evidence", []),
                    "derived_intelligence": payload.get("derived_intelligence", {}),
                },
                ensure_ascii=False,
                default=str,
            ),
            schema_name="investment_synthesis",
            schema={
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "summary": {"type": "string"},
                    "agreements": {"type": "array", "items": {"type": "string"}},
                    "conflicts": {"type": "array", "items": {"type": "string"}},
                    "uncertainties": {"type": "array", "items": {"type": "string"}},
                    "evidence_gaps": {"type": "array", "items": {"type": "string"}},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "summary", "agreements", "conflicts", "uncertainties",
                    "evidence_gaps", "evidence_refs",
                ],
            },
        )
        return {
            "summary": result["summary"],
            "agreements": list(result["agreements"]),
            "conflicts": list(result["conflicts"]),
            "uncertainties": list(result["uncertainties"]),
            "evidence_gaps": list(result["evidence_gaps"]),
            "evidence_refs": list(result["evidence_refs"]),
        }
