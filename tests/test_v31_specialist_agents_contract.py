from __future__ import annotations

from b3_agent.agents.specialist import (
    MarketAnalysisAgent,
    OptionsAnalysisAgent,
    PortfolioAnalysisAgent,
)
from b3_agent.agents.specialists import SpecialistAnalysis, SpecialistContext


class FakeLLM:
    def __init__(self):
        self.calls = []

    def complete_json(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "summary": "summary",
            "findings": ["finding"],
            "risks": ["risk"],
            "evidence_refs": ["obsidian:test.md"],
            "source_refs": ["BRAPI:PETR4"],
        }


def _context():
    return SpecialistContext(
        request="Analyze PETR4",
        deterministic_context={
            "market_analysis": {"price": 42},
            "portfolio_context": {"ticker": "PETR4"},
            "options_analysis": {"premium": 1.2},
            "signals": [{"name": "trend"}],
            "threats": [{"name": "volatility"}],
            "opportunities": [{"id": "op-1"}],
            "action_candidates": [{"id": "op-1"}],
            "risk_analysis": {"assignment": "bounded"},
        },
        retrieved_evidence=(
            {"source_ref": "obsidian:test.md", "snippet": "test", "score": 2},
        ),
    )


def test_specialist_analysis_is_structured():
    result = SpecialistAnalysis(
        agent="market_analysis",
        summary="summary",
        findings=("f",),
        risks=("r",),
        evidence_refs=("e",),
        source_refs=("s",),
    )
    assert result.to_dict()["agent"] == "market_analysis"
    assert result.to_dict()["findings"] == ["f"]


def test_specialists_receive_only_their_focus():
    llm = FakeLLM()
    MarketAnalysisAgent(llm).analyze(_context())
    payload = llm.calls[0]["input_text"]
    assert "market_analysis" in payload
    assert "portfolio_context" not in payload


def test_portfolio_specialist_focus():
    llm = FakeLLM()
    PortfolioAnalysisAgent(llm).analyze(_context())
    payload = llm.calls[0]["input_text"]
    assert "portfolio_context" in payload
    assert "risk_analysis" in payload
    assert "options_analysis" not in payload


def test_options_specialist_focus():
    llm = FakeLLM()
    OptionsAnalysisAgent(llm).analyze(_context())
    payload = llm.calls[0]["input_text"]
    assert "options_analysis" in payload
    assert "opportunities" in payload
    assert "market_analysis" not in payload
