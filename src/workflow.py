"""LangGraph workflow definition for the PO agent.

Defines the graph structure: nodes, edges, and conditional routing.
Nodes are stub classes in Phase 1 — the graph compiles but cannot be
invoked end-to-end until Phase 2.
"""
from langgraph.graph import StateGraph, END

from src.core.workflow_state import POWorkflowState
from src.nodes.classify import ClassifyNode
from src.nodes.extract import ExtractNode
from src.nodes.validate import ValidateNode
from src.nodes.track import TrackNode
from src.nodes.notify import NotifyNode
from src.nodes.report import ReportNode


def should_continue_after_classify(state: POWorkflowState) -> str:
    """Route after classification: continue processing or skip."""
    if state.get("is_valid_po", False):
        return "extract"
    return "report"


def should_continue_after_validate(state: POWorkflowState) -> str:
    """Route after validation: track (complete) or notify (missing info)."""
    missing = state.get("missing_fields", [])
    if missing:
        return "notify"
    return "track"


def build_graph(
    classify_node: ClassifyNode,
    extract_node: ExtractNode,
    validate_node: ValidateNode,
    track_node: TrackNode,
    notify_node: NotifyNode,
    report_node: ReportNode,
):
    """Build and compile the PO workflow graph.

    Graph structure:
        classify → (is_valid_po?) → extract → validate → (missing?) → track → notify → report
                                                                    ↘ notify → report
                 ↘ (not valid) → report

    Returns a compiled LangGraph that can be invoked with a POWorkflowState.
    """
    graph = StateGraph(POWorkflowState)

    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("extract", extract_node)
    graph.add_node("validate", validate_node)
    graph.add_node("track", track_node)
    graph.add_node("notify", notify_node)
    graph.add_node("report", report_node)

    # Entry point
    graph.set_entry_point("classify")

    # Conditional: after classify, either continue or skip
    graph.add_conditional_edges(
        "classify",
        should_continue_after_classify,
        {"extract": "extract", "report": "report"},
    )

    # Linear: extract → validate
    graph.add_edge("extract", "validate")

    # Conditional: after validate, either track (complete) or notify (missing info)
    graph.add_conditional_edges(
        "validate",
        should_continue_after_validate,
        {"track": "track", "notify": "notify"},
    )

    # Linear: track → notify → report → END
    graph.add_edge("track", "notify")
    graph.add_edge("notify", "report")
    graph.add_edge("report", END)

    return graph.compile()
