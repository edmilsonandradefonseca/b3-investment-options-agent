"""Ask for an exact option before interpreting a bounded Lab operation request."""
from __future__ import annotations

import re
import unicodedata

from b3_agent.orchestration.contracts import OrchestratorRequest


def lab_operation_clarification(request: OrchestratorRequest) -> dict | None:
    if request.context.get("workspace") != "Strategy Lab":
        return None
    # Existing structured builders already validate their explicitly selected legs.
    if any(request.context.get(key) for key in (
        "comparison_assets", "option_a", "option_b", "put_candidate_option_ids",
        "funded_switch", "lab_selected_position",
    )):
        return None
    text = "".join(c for c in unicodedata.normalize("NFD", request.task.upper())
                   if not unicodedata.combining(c))
    # Conceptual/thesis questions must retain the evidence/senior path.
    if re.search(r"\b(EXPLIQUE|EXPLICAR|O QUE|COMO FUNCIONA|EVIDENCIAS|TESE)\b", text):
        return None
    operation = re.search(r"\b(ROLAR|ROLAGEM|ENCERRAR|FECHAR|RECOMPRAR)\b", text)
    sale = re.search(r"\bVENDER\s+(?:UMA?\s+)?(?:PUT|CALL)\b", text)
    if not (operation or sale):
        return None
    if not re.search(r"\b(OPCAO|OPCOES|PUT|CALL|CONTRATO)\b", text) and not re.search(r"\b[A-Z]{4}[A-X]\d{1,6}\b", text):
        return None
    if re.search(r"\b[A-Z]{4}[A-X]\d{1,6}\b", text):
        return None
    question = "Qual é o código exato da opção que deseja analisar?"
    return {
        "lab_clarification": {
            "policy_version": "lab-operation-clarification-v1",
            "status": "NEEDS_CLARIFICATION",
            "original_question": request.task,
            "missing_fields": ["option_id"],
            "question": question,
            "reason": "O ativo subjacente não identifica strike, vencimento e lado da posição. Informe o contrato; a análise seguinte deverá verificar sua identidade e a posição vigente.",
        },
        "summary": question,
        "derived_synthesis_status": "NOT_REQUESTED",
        "telemetry": {"llm_calls": 0, "option_chain_calls": 0},
    }
