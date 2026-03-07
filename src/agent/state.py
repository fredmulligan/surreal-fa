"""
Agent state definitions for LangGraph.
Two agents, two state types:
  1. BuildState — for the graph-building agent (the kitchen)
  2. ShockState — for the shock propagation agent (the product)
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import add_messages


class BuildState(TypedDict):
    """State for the graph-building agent."""
    # The industry or topic to build the graph around
    query: str
    # LLM conversation messages
    messages: Annotated[list, add_messages]
    # Which phase we're in
    phase: str  # "discover", "enrich", "expand", "done"
    # Companies discovered so far (names)
    companies_found: list[str]
    # Industries mapped
    industries_found: list[str]
    # Technologies found
    technologies_found: list[str]
    # Commodities found
    commodities_found: list[str]
    # How many enrichment iterations we've done
    iteration: int
    # Maximum iterations before stopping
    max_iterations: int


class ShockState(TypedDict):
    """State for the shock propagation agent."""
    # The shock/event to trace
    query: str
    # LLM conversation messages
    messages: Annotated[list, add_messages]
    # The cascade results
    cascade: dict
    # Current hop depth
    current_hop: int
    # Max hops to trace
    max_hops: int
    # Whether we checked Polymarket
    polymarket_checked: bool
    # Polymarket probability if found
    probability: float | None
