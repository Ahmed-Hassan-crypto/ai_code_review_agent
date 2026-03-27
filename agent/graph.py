"""LangGraph graph - Optimized for Speed."""

from langgraph.graph import StateGraph, START, END
from agent.state import AgentState
from agent.nodes import (
    fetch_diff,
    combined_review,
    combined_fixes_and_score,
    format_review,
    post_review,
)


def build_review_graph():
    """Optimized fast flow:
    fetch_diff → combined_review → combined_fixes → format_review → post_review

    Only 3 LLM calls instead of 6!
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("fetch_diff", fetch_diff)
    graph.add_node("combined_review", combined_review)
    graph.add_node("combined_fixes", combined_fixes_and_score)
    graph.add_node("format_review", format_review)
    graph.add_node("post_review", post_review)

    # Flow
    graph.add_edge(START, "fetch_diff")
    graph.add_edge("fetch_diff", "combined_review")
    graph.add_edge("combined_review", "combined_fixes")
    graph.add_edge("combined_fixes", "format_review")
    graph.add_edge("format_review", "post_review")
    graph.add_edge("post_review", END)

    return graph.compile()


review_graph = build_review_graph()
