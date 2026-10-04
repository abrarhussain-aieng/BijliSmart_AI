"""LangGraph nodes. Each node does one job and returns a partial state update."""
import json
import logging
import re
from functools import wraps

from app.agents.state import AgentState
from app.ai import prompts
from app.ai.mistral import mistral_service
from app.services import bill_analyzer
from app.services.bill_extractor import get_bill_extractor
from app.utils.validators import AIServiceError, AppError, validate_extracted_bill

logger = logging.getLogger(__name__)

# Execution order of the analysis pipeline; `plan` decides which of these run.
PIPELINE = (
    "analyze_bill", "analyze_history", "analyze_consumption", "retrieve_tariff",
    "analyze_appliances", "generate_recommendations", "assistant_response",
)
NODE_DESCRIPTIONS = {
    "analyze_bill": "load the current bill (always needed)",
    "analyze_history": "compare with previous bills, trends and average usage",
    "analyze_consumption": "analyse units, effective rate and consumption drivers",
    "retrieve_tariff": "search the tariff / billing knowledge base (RAG)",
    "analyze_appliances": "estimate appliance consumption and what-if savings",
    "generate_recommendations": "produce energy-saving recommendations",
}
ANALYZE_NODES = [n for n in PIPELINE if n != "assistant_response"]
HOURS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h\b|ghant\w*)", re.I)
REDUCE_RE = re.compile(r"reduc|less|cut|lower|decreas|\bkam\b|save", re.I)


def safe_node(fn):
    """Keep the workflow alive when one node fails; record the error instead."""

    @wraps(fn)
    def wrapper(state: AgentState) -> dict:
        try:
            return fn(state)
        except Exception as exc:
            logger.exception("Node %s failed", fn.__name__)
            msg = exc.message if isinstance(exc, AppError) else "failed unexpectedly"
            return {"errors": [*state.get("errors", []), f"{fn.__name__}: {msg}"]}

    return wrapper


# ---------------- upload flow (errors propagate to the API) ----------------
def extract_bill(state: AgentState) -> dict:
    """OCR/Vision extraction of the uploaded file."""
    raw = get_bill_extractor().extract(state["file_bytes"], state["content_type"])
    return {"bill_data": raw}


def validate_bill(state: AgentState) -> dict:
    """Normalise and verify extracted values."""
    data, warnings = validate_extracted_bill(state["bill_data"])
    return {"bill_data": data, "warnings": warnings, "current_units": data["units"],
            "current_amount": data["amount"], "billing_period": data["billing_month"]}


# ---------------- planning ----------------
def _heuristic_plan(question: str) -> list[str]:
    q = question.lower()
    nodes = ["analyze_bill", "analyze_history", "analyze_consumption"]
    if re.search(r"tariff|rate|slab|tax|charge|fpa|gst|nepra|fesco|lesco|per unit|rs\b", q):
        nodes.append("retrieve_tariff")
    if re.search(r"appliance|\bac\b|fan|heater|geyser|fridge|pump|iron|light|wash|hours?|usage", q):
        nodes.append("analyze_appliances")
    if re.search(r"reduce|save|saving|lower|recommend|tips?|kam|bachat", q):
        nodes += ["analyze_appliances", "generate_recommendations"]
    return nodes


def plan(state: AgentState) -> dict:
    """Decide which analysis nodes are needed for this request."""
    if state["mode"] == "analyze":
        return {"required_nodes": list(ANALYZE_NODES)}
    question = state.get("user_question", "")
    try:
        steps = "\n".join(f"- {k}: {v}" for k, v in NODE_DESCRIPTIONS.items())
        result = mistral_service.chat_json([
            {"role": "system", "content": prompts.PLANNER_PROMPT.format(steps=steps)},
            {"role": "user", "content": question},
        ])
        chosen = [n for n in result.get("nodes", []) if n in NODE_DESCRIPTIONS] if isinstance(result, dict) else []
        nodes = chosen or _heuristic_plan(question)
    except AIServiceError:
        nodes = _heuristic_plan(question)
    if HOURS_RE.search(question) and REDUCE_RE.search(question):
        nodes.append("analyze_appliances")
    required = {"analyze_bill", "assistant_response", *nodes}
    return {"required_nodes": [n for n in PIPELINE if n in required]}


# ---------------- analysis nodes ----------------
@safe_node
def analyze_bill(state: AgentState) -> dict:
    bill = state["tools"].get_current_bill()
    if bill is None:
        return {"bill_data": None, "warnings": [*state.get("warnings", []), "No bill has been uploaded yet."]}
    analysis = {**state.get("analysis", {}), "breakdown": bill_analyzer.bill_breakdown(bill)}
    return {"bill_data": bill, "current_units": bill["units"], "current_amount": bill["amount"],
            "billing_period": bill["billing_month"], "analysis": analysis}


@safe_node
def analyze_history(state: AgentState) -> dict:
    tools = state["tools"]
    summary = tools.compare_previous_bill()
    analysis = {**state.get("analysis", {}), "comparison": summary["comparison"],
                "average_units": summary["average_units"], "average_amount": summary["average_amount"],
                "label": "Calculated Estimate"}
    if not summary["previous"]:
        state_warnings = [*state.get("warnings", []), "No previous bill is available for comparison."]
        return {"historical_bills": summary["history"], "analysis": analysis, "warnings": state_warnings}
    return {"historical_bills": summary["history"], "analysis": analysis}


@safe_node
def analyze_consumption(state: AgentState) -> dict:
    return {"analysis": {**state.get("analysis", {}), "consumption": state["tools"].analyze_consumption()}}


@safe_node
def retrieve_tariff(state: AgentState) -> dict:
    bill = state.get("bill_data") or {}
    query = state.get("user_question") or f"electricity tariff slabs charges {bill.get('tariff') or ''} {bill.get('units') or ''} units"
    info = state["tools"].search_tariff_knowledge(query)
    out: dict = {"tariff_information": info, "retrieved_documents": info["documents"]}
    if info["status"] != "ok":
        out["warnings"] = [*state.get("warnings", []), f"Tariff knowledge unavailable: {info['note']}"]
    return out


def _parse_scenario(question: str, items: list[dict]) -> tuple[str, float] | None:
    """Detect 'reduce <appliance> by N hours' style questions."""
    hours = HOURS_RE.search(question)
    if not hours or not REDUCE_RE.search(question):
        return None
    q = question.lower()
    for item in items:
        base = item["name"].lower().split(" (")[0].strip()
        if base and re.search(rf"\b{re.escape(base)}\b", q):
            return item["name"], float(hours.group(1))
    return None


@safe_node
def analyze_appliances(state: AgentState) -> dict:
    tools = state["tools"]
    estimates = tools.calculate_appliance_usage()
    analysis = dict(state.get("analysis", {}))
    out: dict = {"appliance_estimates": estimates}
    if not estimates["items"]:
        out["warnings"] = [*state.get("warnings", []), "No appliances entered yet, so appliance estimates are unavailable."]
    scenario = _parse_scenario(state.get("user_question", ""), estimates["items"])
    if scenario:
        analysis["scenario"] = tools.calculate_estimated_savings(*scenario)
    elif state.get("user_question") and HOURS_RE.search(state["user_question"]) and REDUCE_RE.search(state["user_question"]):
        analysis["scenario"] = {"error": "Could not match the appliance in your question to the appliances you entered."}
    out["analysis"] = analysis
    return out


@safe_node
def generate_recommendations(state: AgentState) -> dict:
    tools = state["tools"]
    estimates = state.get("appliance_estimates") or tools.calculate_appliance_usage()
    summary = tools.compare_previous_bill()
    recs = bill_analyzer.build_recommendations(estimates, estimates.get("effective_rate"))
    analysis = {**state.get("analysis", {}), "insights": bill_analyzer.build_insights(state.get("bill_data"), summary, estimates),
                "estimated_monthly_savings_kwh": sum(r["estimated_kwh_saved"] for r in recs),
                "estimated_monthly_savings_cost": sum(r["estimated_cost_saved"] or 0 for r in recs) if recs else None}
    if recs:
        try:
            analysis["recommendation_summary"] = mistral_service.chat([
                {"role": "user", "content": prompts.RECOMMENDATION_PROMPT.format(data=json.dumps(recs, default=str))}
            ], temperature=0.3)
        except AIServiceError:
            logger.info("Recommendation summary skipped (AI unavailable).")
    return {"recommendations": recs, "analysis": analysis}


# ---------------- final answer ----------------
def _missing_information(state: AgentState) -> list[str]:
    missing = []
    if not state.get("bill_data"):
        missing.append("No bill uploaded.")
    if len(state.get("historical_bills", [])) < 2:
        missing.append("Fewer than 2 bills stored, so month-to-month comparison is limited.")
    items = (state.get("appliance_estimates") or {}).get("items")
    if "analyze_appliances" in state.get("required_nodes", []) and not items:
        missing.append("No appliances entered.")
    if "retrieve_tariff" in state.get("required_nodes", []) and not state.get("retrieved_documents"):
        missing.append("No tariff knowledge retrieved from the knowledge base.")
    return missing


def _fallback_answer(state: AgentState, missing: list[str]) -> str:
    bill = state.get("bill_data")
    if not bill:
        return "I couldn't find a bill yet. Please upload your electricity bill on the Bills page first."
    lines = [f"[Your bill] {bill['billing_label']}: {bill['units']} units, Rs. {bill['amount']}."]
    comp = state.get("analysis", {}).get("comparison")
    if comp and comp["unit_percentage_change"] is not None:
        lines.append(f"[Estimate] Units changed by {comp['unit_change']:+.0f} ({comp['unit_percentage_change']:+.1f}%) vs {comp['previous_label']}.")
    lines.append("The AI explanation service is unavailable right now, so this is a data-only summary.")
    if missing:
        lines.append("Missing information: " + " ".join(missing))
    return "\n".join(lines)


def assistant_response(state: AgentState) -> dict:
    """Compose the final answer from labelled data sections."""
    missing = _missing_information(state)
    analysis = state.get("analysis", {})
    docs = [{"source": d["source"], "category": d["category"], "excerpt": d["content"][:700]}
            for d in state.get("retrieved_documents", [])]
    context = {
        "USER_BILL_DATA": state.get("bill_data"),
        "USER_BILL_HISTORY": state.get("historical_bills", []),
        "CALCULATED_ESTIMATES": {
            "comparison": analysis.get("comparison"), "average_units": analysis.get("average_units"),
            "consumption": analysis.get("consumption"), "appliances": state.get("appliance_estimates"),
            "what_if_scenario": analysis.get("scenario"),
        },
        "RETRIEVED_TARIFF_KNOWLEDGE": docs,
        "AI_RECOMMENDATION_CANDIDATES": state.get("recommendations", []),
        "MISSING_INFORMATION": missing,
    }
    messages = [{"role": "system", "content": prompts.ASSISTANT_SYSTEM_PROMPT}, *state.get("chat_history", [])[-6:],
                {"role": "user", "content": f"DATA:\n{json.dumps(context, default=str)}\n\nQUESTION: {state['user_question']}"}]
    try:
        answer = mistral_service.chat(messages, temperature=0.2)
    except AIServiceError as exc:
        answer = _fallback_answer(state, missing) if exc.status_code != 503 else \
            "The AI assistant is not configured yet (missing MISTRAL_API_KEY on the server)."
    return {"final_response": answer or _fallback_answer(state, missing)}
