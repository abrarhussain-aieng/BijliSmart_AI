"""LangGraph workflow.

upload : START -> extract_bill -> validate_bill -> END
analyze: START -> plan -> [analysis nodes] -> END
chat   : START -> plan -> [only the nodes the question needs] -> assistant_response -> END
"""
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agents import nodes
from app.agents.state import AgentState


def _router(current: str | None):
    """Return the next required node after `current` (pipeline order), or END."""

    def route(state: AgentState) -> str:
        required = set(state.get("required_nodes", []))
        start = nodes.PIPELINE.index(current) + 1 if current else 0
        return next((n for n in nodes.PIPELINE[start:] if n in required), END)

    return route


@lru_cache
def get_graph():
    """Build and compile the graph once."""
    graph = StateGraph(AgentState)
    graph.add_node("extract_bill", nodes.extract_bill)
    graph.add_node("validate_bill", nodes.validate_bill)
    graph.add_node("plan", nodes.plan)
    for name in nodes.PIPELINE:
        graph.add_node(name, getattr(nodes, name))

    graph.add_conditional_edges(
        START, lambda s: "extract_bill" if s["mode"] == "upload" else "plan",
        {"extract_bill": "extract_bill", "plan": "plan"},
    )
    graph.add_edge("extract_bill", "validate_bill")
    graph.add_edge("validate_bill", END)

    targets = {n: n for n in nodes.PIPELINE} | {END: END}
    graph.add_conditional_edges("plan", _router(None), targets)
    for name in nodes.PIPELINE:
        if name == "assistant_response":
            graph.add_edge(name, END)
        else:
            graph.add_conditional_edges(name, _router(name), targets)
    return graph.compile()


def run_graph(initial_state: dict) -> dict:
    """Execute the workflow and return the final state."""
    return get_graph().invoke(initial_state)
