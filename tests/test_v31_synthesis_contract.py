import json

from b3_agent.agents.context import AgentContext
from b3_agent.agents.synthesis import SynthesisAgent


class FakeLLM:
    def __init__(self):
        self.calls = []

    def complete_json(self, *, instructions, input_text, schema_name, schema):
        self.calls.append({
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
