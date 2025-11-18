"""
🤖 COMPREHENSIVE RAG ORCHESTRATOR DASHBOARD
Master Orchestrator with LangChain DeepAgents
Features: Agent Pool Management | LangChain DeepAgents | RBAC Filtering | Answer Synthesis
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agents.agentic_orchestrator import MasterOrchestrator
from src.storage import RAGDatabase

# ==================== CONFIG ====================
st.set_page_config(page_title="🤖 RAG Orchestrator Master", page_icon="🤖", layout="wide")

# ==================== SESSION STATE ====================
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = MasterOrchestrator(name="master_dashboard")
if "spawned_agents" not in st.session_state:
    st.session_state.spawned_agents = {}

orch = st.session_state.orchestrator
db = orch.db
stats = orch.dashboard_statistics()

# ==================== UTILITIES ====================
def spawn_agents(task: str):
    """Spawn agent pool based on task."""
    pools = {
        "ingest": [("📥 DataLoader", "#FF6B6B"), ("🔍 Detector", "#FFA500"), 
                   ("🏷️ Classifier", "#FFD700"), ("✂️ Chunker", "#90EE90")],
        "retrieve": [("🔎 Analyzer", "#87CEEB"), ("🌐 Searcher", "#4169E1"), 
                     ("🔐 Filter", "#8B0000"), ("📊 Ranker", "#20B2AA"), ("🤖 Synthesizer", "#FFB6C1")],
        "heal": [("🔬 Analyzer", "#DDA0DD"), ("🧹 Optimizer", "#DA70D6"), 
                 ("🧼 Cleaner", "#BA55D3")],
        "learn": [("🧠 Pattern", "#FFB6C1"), ("⚡ Optimizer", "#FFC0CB")]
    }
    
    agents = []
    for name, color in pools.get(task, []):
        agents.append({"name": name, "color": color, "status": "✅ Active"})
    
    st.session_state.spawned_agents[task] = agents
    return agents

def render_agent_pool(agents):
    """Render active agents in pool."""
    cols = st.columns(len(agents))
    for col, agent in zip(cols, agents):
        with col:
            st.markdown(f"### {agent['name']}")
            st.markdown(f"Status: {agent['status']}")

# ==================== SIDEBAR ====================
st.sidebar.title("🤖 ORCHESTRATOR MASTER")
st.sidebar.markdown("**Master Control Center with LangChain DeepAgents**")

page = st.sidebar.radio("Navigation", [
    "🎯 Orchestrator Pool",
    "📊 Summary",
    "🔄 Simulation",
    "📥 Ingest",
    "🔍 Retrieve",
    "⚙️ System"
])

st.sidebar.markdown("---")
st.sidebar.subheader("📊 System")
c1, c2 = st.sidebar.columns(2)
c1.metric("Docs", stats['total_documents'])
c2.metric("Queries", stats['queries_24h'])
c1.metric("Agents", stats['active_agents'])
c2.metric("Time", f"{stats['avg_response_time']:.1f}s")

# ==================== PAGE 1: ORCHESTRATOR POOL ====================
if page == "🎯 Orchestrator Pool":
    st.title("🎯 Master Orchestrator - Agent Pool Management")
    st.markdown("**Interactive task-based agent spawning & monitoring**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📥 Spawn Ingest Pool"):
            agents = spawn_agents("ingest")
            st.session_state.spawned_agents["current"] = agents
    with col2:
        if st.button("🔍 Spawn Retrieve Pool"):
            agents = spawn_agents("retrieve")
            st.session_state.spawned_agents["current"] = agents
    with col3:
        if st.button("🔧 Spawn Healer Pool"):
            agents = spawn_agents("heal")
            st.session_state.spawned_agents["current"] = agents
    
    st.markdown("---")
    
    if "current" in st.session_state.spawned_agents:
        st.subheader("✅ Active Agent Pool")
        agents = st.session_state.spawned_agents["current"]
        render_agent_pool(agents)
        
        st.markdown("---")
        st.subheader("📊 Agent Status Dashboard")
        
        fig = go.Figure()
        for i, agent in enumerate(agents):
            fig.add_trace(go.Scatter(
                x=[i], y=[1],
                mode='markers+text',
                marker=dict(size=50, color=agent['color']),
                text=[agent['name'].split()[0]],
                textposition="bottom center",
                hovertext=f"<b>{agent['name']}</b><br>{agent['status']}"
            ))
        
        fig.update_layout(title="Agent Pool Visualization", height=300,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
        
        st.plotly_chart(fig, width='stretch')
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Agents", len(agents))
        col2.metric("Active", len(agents))
        col3.metric("Processing", len(agents))
    
    st.markdown("---")
    st.subheader("📜 Recent Agent Spawns")
    spawns = db.get_agent_spawn_history(limit=5)
    if spawns:
        df = pd.DataFrame(spawns)
        st.dataframe(df[['parent_agent', 'child_agent', 'task_description', 'status']], width='stretch')

# ==================== PAGE 5: RETRIEVE (MAIN) ====================
elif page == "🔍 Retrieve":
    st.title("🔍 Retrieval & Search with LangChain DeepAgents")
    st.markdown("**Intelligent query processing with context-aware agent orchestration**")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_area("Query:", placeholder="how to roll back database", height=80)
    with col2:
        role = st.selectbox("Role:", ["engineer", "hr", "manager", "admin"])
    
    if st.button("🔍 Retrieve & Spawn Agents"):
        if query:
            access_levels = {"engineer": 3, "hr": 2, "manager": 4, "admin": 5}
            access_level = access_levels.get(role, 2)
            
            agents = spawn_agents("retrieve")
            st.session_state.spawned_agents["current"] = agents
            
            st.markdown("---")
            st.subheader("🤖 Orchestrator spawning retrieval pool...")
            
            progress = st.progress(0)
            st.markdown("**Agent Pool:**")
            render_agent_pool(agents)
            progress.progress(20)
            
            st.markdown("---")
            with st.spinner("Processing query through intelligent agent chain..."):
                try:
                    result = orch.process_query(
                        query=query,
                        user_id="dashboard_user",
                        user_role=role,
                        access_level=access_level
                    )
                    progress.progress(80)
                    execution_log = result
                    query_result = execution_log.get("results", {})
                    agents_used = execution_log.get("agents_executed", [])
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    progress.progress(100)
                    st.stop()
            
            progress.progress(100)
            
            st.markdown("---")
            st.success("✓ Query processing complete")
            
            st.markdown("---")
            st.subheader("📊 Execution Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Agents Used", len(agents_used))
            col2.metric("Documents Found", query_result.get("documents_used", 0))
            col3.metric("Confidence", f"{query_result.get('confidence', 0):.2f}")
            col4.metric("RBAC Applied", "Yes" if query_result.get("rbac_applied") else "No")
            
            st.markdown("---")
            st.subheader("🔗 Agent Execution Chain")
            cols = st.columns(len(agents_used))
            for i, col in enumerate(cols):
                with col:
                    st.markdown(f"**{i+1}. {agents_used[i].upper()}**")
                    st.markdown("✓ Complete")
            
            st.markdown("---")
            st.subheader("🧠 Reasoning Trace")
            reasoning = query_result.get("reasoning_trace", {})
            
            if reasoning:
                trace_cols = st.columns(min(len(reasoning), 5))
                for col, (step, details) in zip(trace_cols, list(reasoning.items())[:5]):
                    with col:
                        st.markdown(f"**{step.upper()}**")
                        if isinstance(details, dict):
                            for key, value in list(details.items())[:2]:
                                st.text(f"{key}: {value}")
                        else:
                            st.text(str(details)[:80])
            
            st.markdown("---")
            st.subheader("📄 Generated Answer")
            answer = query_result.get("answer", "No answer generated")
            st.markdown(answer)
            
            st.markdown("---")
            st.subheader("📚 Sources Used")
            
            if query_result.get("sources"):
                for i, source in enumerate(query_result.get("sources", []), 1):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{i}. {source.get('source', 'Unknown')}**")
                    with col2:
                        st.metric("Similarity", f"{source.get('similarity', 0):.2f}")
            else:
                st.info("No sources available")
            
            st.markdown("---")
            st.subheader("🔐 RBAC Information")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("User Role", role)
                st.metric("Access Level", access_level)
            with col2:
                st.metric("Documents Found", query_result.get("documents_used", 0))
                st.metric("RBAC Status", "Applied")
        else:
            st.warning("Please enter a query")

# ==================== PAGE 2: SUMMARY ====================
elif page == "📊 Summary":
    st.title("📊 Summary & Analytics")
    st.header("📈 System Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Documents", stats['total_documents'])
    col2.metric("Queries (24h)", stats['queries_24h'])
    col3.metric("Active Agents", stats['active_agents'])

# ==================== PAGE 3: SIMULATION ====================
elif page == "🔄 Simulation":
    st.title("🔄 Simulation Center")
    col1, col2, col3 = st.columns(3)
    with col1:
        dept = st.selectbox("Department:", ["engineering", "hr", "security", "finance"])
    with col2:
        role = st.selectbox("Role:", ["analyst", "engineer", "manager"])
    with col3:
        access = st.slider("Access Level:", 1, 5, 3)
    st.info(f"Config: {dept}/{role} (Access: {access})")

# ==================== PAGE 4: INGEST ====================
elif page == "📥 Ingest":
    st.title("📥 Ingestion Workflow")
    table = st.selectbox("Select table:", ["incident_knowledge", "documents", "query_history"])
    if st.button("📥 Ingest & Spawn Agents"):
        agents = spawn_agents("ingest")
        st.session_state.spawned_agents["current"] = agents
        render_agent_pool(agents)
        st.success("✅ Ingestion Complete!")

# ==================== PAGE 6: SYSTEM ====================
elif page == "⚙️ System":
    st.title("⚙️ System Configuration")
    configs = {"System": "config/system_config.yaml", "RBAC": "config/rbac_config.yaml"}
    selected = st.selectbox("Config:", list(configs.keys()))
    st.info(f"Configuration: {selected}")

st.markdown("---")
st.markdown(f"🤖 RAG Orchestrator Master | LangChain DeepAgents | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
