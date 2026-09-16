from __future__ import annotations

from pathlib import Path

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.config import settings
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.llm.client import OpenAIResponsesClient

from .orchestrator import configure_workflow
from .workflow import build_workflow


def configure_default_workflow(*, vault_path: Path | None = None) -> None:
    """Compose and register the production V3.1 workflow.

    The composition root owns concrete dependencies. The orchestrator and
    transport layers remain independent of OpenAI, Obsidian and LangGraph
    construction details.
    """
    resolved_vault = (
        Path(vault_path).expanduser().resolve()
        if vault_path is not None
        else settings.obsidian_vault
    )
    if resolved_vault is None:
        raise RuntimeError(
            "B3_AGENT_OBSIDIAN_VAULT is not configured; cannot compose the workflow"
        )
    if not resolved_vault.is_dir():
        raise FileNotFoundError(f"Obsidian vault does not exist: {resolved_vault}")
    if not settings.llm_enabled:
        raise RuntimeError(
            "B3_AGENT_LLM_ENABLED is false; cannot compose the reasoning workflow"
        )

    workflow = build_workflow(
        retriever=ObsidianRetriever(ObsidianKnowledgeStore(resolved_vault)),
        reasoning_agent=InvestmentReasoningAgent(
            OpenAIResponsesClient(model=settings.llm_model)
        ),
        risk_validator=RiskValidator(),
    )
    configure_workflow(workflow)
