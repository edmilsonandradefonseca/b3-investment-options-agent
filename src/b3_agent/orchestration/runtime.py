from __future__ import annotations

from pathlib import Path
from typing import Any

from b3_agent.agents.reasoning import InvestmentReasoningAgent
from b3_agent.agents.risk_validator import RiskValidator
from b3_agent.config import settings
from b3_agent.knowledge.obsidian import ObsidianKnowledgeStore
from b3_agent.knowledge.retrieval import ObsidianRetriever
from b3_agent.llm.client import OpenAIResponsesClient
from b3_agent.schemas.position import PortfolioContext
from b3_agent.schemas.opportunity import OpportunitySet

from .orchestrator import configure_workflow
from .workflow import build_workflow


def configure_default_workflow(
    *,
    vault_path: Path | None = None,
    portfolio_context: PortfolioContext | dict[str, Any] | None = None,
    opportunity_set: OpportunitySet | None = None,
) -> None:
    """Compose and register the production V3.1 workflow.

    Deterministic portfolio/opportunity context is injected at the composition
    root. The workflow and reasoning layers only consume that context; they do
    not own provider access or recompute portfolio/opportunity facts.
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

    deterministic_defaults: dict[str, Any] = {}
    if portfolio_context is not None:
        deterministic_defaults["portfolio_context"] = portfolio_context
    if opportunity_set is not None:
        deterministic_defaults["opportunity_set"] = opportunity_set

    if deterministic_defaults:
        def invoke_with_deterministic_context(state):
            initial_state = {**deterministic_defaults, **state}
            return workflow.invoke(initial_state)

        configure_workflow(invoke_with_deterministic_context)
    else:
        configure_workflow(workflow)
