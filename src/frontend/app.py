"""
Surreal FA — Streamlit frontend.

Chat interface on the left, visualization on the right.
Each tool returns a known shape, so we know how to render it.
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

from src.frontend.agent import get_agent

st.set_page_config(page_title="Surreal FA", layout="wide")
st.title("Surreal FA — Economic Knowledge Graph")

# --- Session state ---
if "agent" not in st.session_state:
    st.session_state.agent = get_agent()
if "response" not in st.session_state:
    st.session_state.response = None
if "tool_data" not in st.session_state:
    st.session_state.tool_data = None
if "user_query" not in st.session_state:
    st.session_state.user_query = None


def extract_tool_data(result):
    """Pull structured tool output from agent result messages."""
    for msg in reversed(result["messages"]):
        if hasattr(msg, "type") and msg.type == "tool":
            try:
                return json.loads(msg.content)
            except (json.JSONDecodeError, TypeError):
                pass
    return None


def render_supply_chain_inputs(data):
    """Render a supply_chain_inputs result as a pyvis network graph."""
    net = Network(height="500px", width="100%", directed=True, bgcolor="#0e1117", font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    # Support multi-industry center nodes
    center_ids = set()
    if data.get("center_ids"):
        for c in data["center_ids"]:
            center_ids.add(c["id"])
            net.add_node(c["id"], label=c["name"], color="#ff6b6b", size=30, font={"size": 16, "color": "white"})
    else:
        center = data["industry"]
        center_name = data.get("industry_name", center)
        center_ids.add(center)
        net.add_node(center, label=center_name, color="#ff6b6b", size=30, font={"size": 16, "color": "white"})

    # Figure out which nodes are direct inputs (depth 1) vs depth 2
    direct_input_ids = set()
    if data.get("edges"):
        for e in data["edges"]:
            if e["to_id"] in center_ids:
                direct_input_ids.add(e["from_id"])

    # Add all input nodes
    for inp in data.get("inputs", []):
        node_id = inp["id"] or inp["name"]
        if node_id in direct_input_ids:
            color = "#4ecdc4"  # teal — direct input
            size = 22
        else:
            color = "#ffe66d"  # yellow — depth 2
            size = 16
        net.add_node(node_id, label=inp["name"], color=color, size=size, font={"size": 12, "color": "white"})

    # Add edges
    for e in data.get("edges", []):
        from_id = e["from_id"] or e["from_name"]
        to_id = e["to_id"] or e["to_name"]
        net.add_edge(from_id, to_id, color="#888888", width=2)

    html = net.generate_html()
    components.html(html, height=520, scrolling=False)


def render_forward_impact(data):
    """Render a forward_impact result as a pyvis network graph."""
    net = Network(height="500px", width="100%", directed=True, bgcolor="#0e1117", font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    # Support multi-industry center nodes
    center_ids = set()
    if data.get("center_ids"):
        for c in data["center_ids"]:
            center_ids.add(c["id"])
            net.add_node(c["id"], label=c["name"], color="#ff6b6b", size=30, font={"size": 16, "color": "white"})
    else:
        center = data["industry"]
        center_name = data.get("industry_name", center)
        center_ids.add(center)
        net.add_node(center, label=center_name, color="#ff6b6b", size=30, font={"size": 16, "color": "white"})

    # Direct dependents = edges where from_id is a center node
    direct_dep_ids = set()
    for e in data.get("edges", []):
        if e["from_id"] in center_ids:
            direct_dep_ids.add(e["to_id"])

    for dep in data.get("dependents", []):
        node_id = dep["id"] or dep["name"]
        if node_id in direct_dep_ids:
            color = "#f9a825"  # orange — direct dependent
            size = 22
        else:
            color = "#ce93d8"  # purple — depth 2
            size = 16
        net.add_node(node_id, label=dep["name"], color=color, size=size, font={"size": 12, "color": "white"})

    for e in data.get("edges", []):
        from_id = e["from_id"] or e["from_name"]
        to_id = e["to_id"] or e["to_name"]
        net.add_edge(from_id, to_id, color="#888888", width=2)

    html = net.generate_html()
    components.html(html, height=520, scrolling=False)


def render_company_exposure(data):
    """Render company_exposure as a table."""
    import pandas as pd
    companies = data.get("companies", [])
    if not companies:
        return

    df = pd.DataFrame(companies)
    df = df[["name", "ticker", "market_cap", "sector"]].copy()
    df.columns = ["Company", "Ticker", "Market Cap", "Sector"]

    # Format market cap
    def fmt_mcap(v):
        if not v or v == 0:
            return "—"
        if v >= 1e12:
            return f"${v/1e12:.1f}T"
        if v >= 1e9:
            return f"${v/1e9:.1f}B"
        if v >= 1e6:
            return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"

    df["Market Cap"] = df["Market Cap"].apply(fmt_mcap)
    df["Ticker"] = df["Ticker"].fillna("—")
    df["Sector"] = df["Sector"].fillna("—")

    industry_name = data.get("industry_name", data["industry"])
    st.caption(f"{len(companies)} companies in **{industry_name}**")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_company_industries(data):
    """Render company_industries as a pyvis network — company at center, industries around it."""
    net = Network(height="500px", width="100%", directed=True, bgcolor="#0e1117", font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    comp_id = data["company"]
    comp_name = data.get("company_name", comp_id)
    ticker = data.get("ticker")
    label = f"{comp_name}\n({ticker})" if ticker else comp_name

    # Company node — blue
    net.add_node(comp_id, label=label, color="#4fc3f7", size=30, font={"size": 16, "color": "white"})

    for ind in data.get("industries", []):
        node_id = ind["id"] or ind["name"]
        net.add_node(node_id, label=ind["name"], color="#4ecdc4", size=20, font={"size": 12, "color": "white"})
        net.add_edge(comp_id, node_id, color="#888888", width=2)

    st.caption(f"**{comp_name}** operates in {len(data.get('industries', []))} industries")
    html = net.generate_html()
    components.html(html, height=520, scrolling=False)


def render_shock_propagate(data):
    """Render shock propagation — industry cascade graph + affected companies table."""
    # Industry cascade graph
    net = Network(height="350px", width="100%", directed=True, bgcolor="#0e1117", font_color="white")
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    center_ids = set()
    if data.get("center_ids"):
        for c in data["center_ids"]:
            center_ids.add(c["id"])
            net.add_node(c["id"], label=c["name"], color="#ff6b6b", size=30, font={"size": 16, "color": "white"})
    else:
        center_ids.add(data["industry"])
        net.add_node(data["industry"], label=data.get("industry_name", data["industry"]),
                     color="#ff6b6b", size=30, font={"size": 16, "color": "white"})

    # Direct vs depth-2 dependents
    direct_ids = set()
    for e in data.get("edges", []):
        if e["from_id"] in center_ids:
            direct_ids.add(e["to_id"])

    for ind in data.get("affected_industries", []):
        node_id = ind["id"] or ind["name"]
        if node_id in direct_ids:
            color = "#f9a825"
            size = 22
        else:
            color = "#ce93d8"
            size = 16
        net.add_node(node_id, label=ind["name"], color=color, size=size, font={"size": 12, "color": "white"})

    for e in data.get("edges", []):
        net.add_edge(e["from_id"] or e["from_name"], e["to_id"] or e["to_name"], color="#888888", width=2)

    n_ind = len(data.get("affected_industries", []))
    n_comp = len(data.get("affected_companies", []))
    st.caption(f"Shock hits **{n_ind}** industries, exposing **{n_comp}** companies")
    html = net.generate_html()
    components.html(html, height=370, scrolling=False)

    # Companies table
    companies = data.get("affected_companies", [])
    if companies:
        import pandas as pd
        df = pd.DataFrame(companies)
        df = df.rename(columns={"name": "Company", "ticker": "Ticker", "market_cap": "Market Cap"})
        df = df[["Company", "Ticker", "Market Cap"]]

        def fmt_mcap(v):
            if v is None or (isinstance(v, float) and v != v):
                return "—"
            if v >= 1e12:
                return f"${v/1e12:.1f}T"
            if v >= 1e9:
                return f"${v/1e9:.1f}B"
            if v >= 1e6:
                return f"${v/1e6:.0f}M"
            return f"${v:,.0f}"

        df["Market Cap"] = df["Market Cap"].apply(fmt_mcap)
        df["Ticker"] = df["Ticker"].fillna("—")
        st.dataframe(df, use_container_width=True, hide_index=True, height=250)


RENDERERS = {
    "supply_chain_inputs": render_supply_chain_inputs,
    "forward_impact": render_forward_impact,
    "company_exposure": render_company_exposure,
    "company_industries": render_company_industries,
    "shock_propagate": render_shock_propagate,
}

# --- Layout ---
chat_col, viz_col = st.columns([1, 1])

with chat_col:
    st.subheader("Ask a question")

    if user_input := st.chat_input("e.g. What goes into a solar panel?"):
        # Run agent, store results, rerun to render clean
        agent = st.session_state.agent
        result = agent.invoke({"messages": [("user", user_input)]})
        st.session_state.user_query = user_input
        st.session_state.response = result["messages"][-1].content
        st.session_state.tool_data = extract_tool_data(result)
        st.rerun()

    # Render the single current Q&A
    if st.session_state.user_query:
        with st.chat_message("user"):
            st.write(st.session_state.user_query)
    if st.session_state.response:
        with st.chat_message("assistant"):
            st.write(st.session_state.response)

with viz_col:
    st.subheader("Visualization")
    data = st.session_state.tool_data
    if data and data.get("tool") in RENDERERS and (data.get("inputs") or data.get("dependents") or data.get("companies") or data.get("industries") or data.get("affected_industries") or data.get("affected_companies")):
        RENDERERS[data["tool"]](data)
    elif data and data.get("message"):
        st.warning(data["message"])
    else:
        st.info("Ask a question to see the graph visualization.")
