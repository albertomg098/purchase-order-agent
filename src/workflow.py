"""LangGraph workflow definition for the PO agent."""
from langgraph.graph import StateGraph, END

from src.core.workflow_state import POWorkflowState


def should_continue_after_classify(state: POWorkflowState) -> str:
    """Route after classification: continue processing or skip to report."""
    if state.get("is_valid_po", False):
        return "extract"
    return "report"


def build_graph(nodes: dict):
    """Build and compile the PO workflow graph.

    Graph structure:
        classify → (is_valid_po?) → extract → validate → track → notify → report → END
                 ↘ (not valid) → report → END

    Args:
        nodes: Dict mapping node names to callable node instances.

    Returns a compiled LangGraph that can be invoked with a POWorkflowState.
    """
    graph = StateGraph(POWorkflowState)

    # Add nodes
    graph.add_node("classify", nodes["classify"])
    graph.add_node("extract", nodes["extract"])
    graph.add_node("validate", nodes["validate"])
    graph.add_node("track", nodes["track"])
    graph.add_node("notify", nodes["notify"])
    graph.add_node("report", nodes["report"])

    # Entry point
    graph.set_entry_point("classify")

    # Conditional: after classify, either continue or skip to report
    graph.add_conditional_edges(
        "classify",
        should_continue_after_classify,
        {"extract": "extract", "report": "report"},
    )

    # Linear: extract → validate → track → notify → report → END
    graph.add_edge("extract", "validate")
    graph.add_edge("validate", "track")
    graph.add_edge("track", "notify")
    graph.add_edge("notify", "report")
    graph.add_edge("report", END)

    return graph.compile()
