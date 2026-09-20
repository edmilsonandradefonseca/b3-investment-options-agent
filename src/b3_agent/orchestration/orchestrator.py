from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from .contracts import B3State, OrchestratorRequest, OrchestratorResponse


class WorkflowInvoker(Protocol):
    """Minimal boundary required by the logical orchestrator contract."""

    def invoke(self, state: B3State) -> dict[str, Any]: ...


_configured_workflow: WorkflowInvoker | Callable[[B3State], dict[str, Any]] | None = None


def configure_workflow(
    workflow: WorkflowInvoker | Callable[[B3State], dict[str, Any]],
) -> None:
    """Configure the LangGraph workflow used by ``b3_orchestrator``.

    Runtime composition belongs to the application/server layer. Keeping the
    workflow behind this small boundary prevents clients from knowing how the
    workflow is constructed.
    """

    global _configured_workflow
    _configured_workflow = workflow


def b3_orchestrator(
    task: str,
    ticker: str | None = None,
    context: dict[str, Any] | None = None,
) -> OrchestratorResponse:
    """Invoke the single logical B3 investment-workflow contract.

    This function is intentionally transport-agnostic. HTTP/API concerns belong
    to the future B3 Orchestrator Server; LangGraph remains the workflow brain.
    """

    request = OrchestratorRequest.from_inputs(task, ticker, context)
    workflow = _configured_workflow
    if workflow is None:
        raise RuntimeError("B3 orchestrator workflow is not configured")

    initial_state: B3State = {
        "user_question": request.task,
        "ticker": request.ticker,
        **request.context,
    }

    if hasattr(workflow, "invoke"):
        final_state = workflow.invoke(initial_state)
    else:
        final_state = workflow(initial_state)

    return _response_from_state(final_state)


def _response_from_state(state: dict[str, Any]) -> OrchestratorResponse:
    sources = tuple(state.get("sources", ()))
    audit = tuple(state.get("audit", ()))
    if "dashboard_snapshot" in state:
        result = {"dashboard_snapshot": state["dashboard_snapshot"]}
    else:
        result = {
            key: value
            for key, value in state.items()
            if key not in {"sources", "audit", "status"}
        }
    return OrchestratorResponse(
        status=str(state.get("status", "COMPLETED")),
        result=result,
        sources=sources,
        audit=audit,
    )
