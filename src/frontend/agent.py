"""
Surreal FA — LangGraph agent.

The agent's only job: classify the user's question, pick a tool,
fill in the parameters. The tool runs a fixed SurrealQL query.
No freeform query generation.
"""

import os
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.frontend.tools import ALL_TOOLS

# Try Streamlit secrets first, fall back to env vars / .env
try:
    import streamlit as st
    _secrets = dict(st.secrets)
except Exception:
    _secrets = {}

def _get(key, default=None):
    """Read from Streamlit secrets, then env vars, then default."""
    return _secrets.get(key) or os.getenv(key, default)

SYSTEM_PROMPT = """You are Surreal FA, an economic knowledge graph assistant.

You have access to tools that query a graph of industries, companies, and their
supply chain relationships. Each tool runs a fixed query — your job is to pick
the right tool and fill in the parameters based on the user's question.

The graph contains:
- Industries (e.g. steel, copper, solar_panel, semiconductor)
- Companies (e.g. Tesla, TSMC, Rio Tinto)
- Supply chain edges: industry_uses_input (what goes into what)
- Company edges: operates_in (which companies are in which industries)

Industry IDs use underscores and lowercase: "solar_panel", "copper_extraction", "steel".
Company IDs are also lowercase with underscores: "tesla", "rio_tinto".

When the user asks a question, pick the right tool. If no tool fits, say so.
Do not make up data. Only return what the graph gives you.

CRITICAL FORMATTING RULE: After a tool returns results, respond with ONE short sentence
stating the numbers. Examples:
- "Lithium shock: 8 affected industries, 88 exposed companies."
- "Steel has 14 direct inputs."
- "Found 94 companies across 4 battery industries."

Do NOT explain, interpret, editorialize, or list individual results. The visualization
panel shows everything. Your ONLY job is to state the counts. Nothing else.
"""


def get_agent():
    """Build and return the LangGraph agent (lazy init)."""
    llm = AzureChatOpenAI(
        azure_endpoint=_get("AZURE_OPENAI_ENDPOINT"),
        api_key=_get("AZURE_OPENAI_API_KEY"),
        azure_deployment=_get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        api_version=_get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
    )
    return create_react_agent(
        model=llm,
        tools=ALL_TOOLS,
        prompt=SYSTEM_PROMPT,
    )
