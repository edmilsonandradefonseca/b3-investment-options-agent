import json

from b3_agent.agents.context import AgentContext
from b3_agent.agents.synthesis import SynthesisAgent


class FakeLLM:
    def __init__(self):
        self.calls = []

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        self.calls.append({
            "instructions": instructions,
            "schema_name": schema_name,
            "input": json.loads(input_text),
            "schema": schema,
        })
        return {
            "summary": "Aligned specialist view.",
            "agreements": ["Shared evidence supports the same context."],
            "conflicts": [],
            "uncertainties": ["Future conditions may change."],
            "evidence_gaps": [],
            "evidence_refs": ["obsidian:PETR4.md"],
        }


def test_synthesis_separates_deterministic_facts_from_specialist_outputs():
    llm = FakeLLM()
    agent = SynthesisAgent(llm)
    context = AgentContext(
        request="Assess PETR4",
        deterministic_context={
            "market_analysis": {"price": 38.0},
            "options_analysis": {"premium": 1.2},
            "risk_analysis": {"status": "VALIDATED"},
            "market_agent_analysis": {"agent": "market_analysis"},
            "portfolio_agent_analysis": {"agent": "portfolio_analysis"},
            "options_agent_analysis": {"agent": "options_analysis"},
        },
        retrieved_evidence=({"source_ref": "obsidian:PETR4.md"},),
        derived_intelligence={
            "local_evidence_dossier": {
                "status": "READY",
                "summary": "background only",
            }
        },
    )

    result = agent.synthesize(context)

    assert result["summary"] == "Aligned specialist view."
    assert len(llm.calls) == 1
    call = llm.calls[0]
    assert call["schema_name"] == "investment_synthesis"
    assert call["input"]["deterministic_facts"] == {
        "market_analysis": {"price": 38.0},
        "options_analysis": {"premium": 1.2},
        "risk_analysis": {"status": "VALIDATED"},
    }
    assert call["input"]["specialist_analyses"] == {
        "market_agent_analysis": {"agent": "market_analysis"},
        "portfolio_agent_analysis": {"agent": "portfolio_analysis"},
        "options_agent_analysis": {"agent": "options_analysis"},
    }
    assert call["input"]["retrieved_evidence"] == [{"source_ref": "obsidian:PETR4.md"}]


def test_synthesis_receives_derived_intelligence_as_separate_context():
    llm = FakeLLM()
    agent = SynthesisAgent(llm)
    agent.synthesize(
        AgentContext(
            request="Assess PETR4",
            deterministic_context={"market_analysis": {"price": 38.0}},
            retrieved_evidence=({"source_ref": "CVM:1"},),
            derived_intelligence={
                "local_evidence_dossier": {
                    "status": "READY",
                    "summary": "pre-analysis",
                }
            },
        )
    )

    payload = llm.calls[0]["input"]
    assert payload["retrieved_evidence"] == [{"source_ref": "CVM:1"}]
    assert payload["derived_intelligence"]["local_evidence_dossier"]["status"] == "READY"
    assert "local_evidence_dossier" not in payload["deterministic_facts"]


def test_synthesis_prompt_assigns_clear_roles_and_requires_decision_relevant_evidence():
    llm = FakeLLM()
    SynthesisAgent(llm).synthesize(
        AgentContext(
            request="Analyze PETR4",
            deterministic_context={"market_analysis": {"price": 51.2}},
            retrieved_evidence=({"source_ref": "research:PETR4"},),
        )
    )

    instructions = llm.calls[0]["instructions"]
    assert "serviços determinísticos B3 são a fonte de verdade" in instructions
    assert "João Resolve e a pesquisa interpretam contexto" in instructions
    assert "histórico pessoal apenas quando houver execuções/outcomes pertinentes" in instructions
    assert "preço versus médias, RSI, MACD, volatilidade e drawdown" in instructions
    assert "VALIDATED' ou 'PASS' descreve somente a validação recebida" in instructions
    assert "dado específico ausente, por que importa" in instructions
