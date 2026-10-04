"""Shared LangGraph state."""
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    mode: str                      # "upload" | "analyze" | "chat"
    # upload flow
    file_bytes: bytes
    content_type: str
    # shared context
    tools: Any                     # AgentTools bound to this request
    bill_id: int | None
    bill_data: dict | None
    current_units: float | None
    current_amount: float | None
    billing_period: str | None
    tariff_information: dict
    historical_bills: list[dict]
    appliance_estimates: dict
    retrieved_documents: list[dict]
    analysis: dict
    recommendations: list[dict]
    # chat flow
    user_question: str
    chat_history: list[dict]
    required_nodes: list[str]
    final_response: str
    # diagnostics
    warnings: list[str]
    errors: list[str]
