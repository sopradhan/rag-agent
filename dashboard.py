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

from src.orchestrator import MasterOrchestrator
from src.storage import RAGDatabase
from src.agents.parent_agents import IngestionAgent, RetrievalAgent, HealingAgent
from src.abstraction import Document

# ==================== CONFIG ====================
st.set_page_config(page_title="🤖 RAG Orchestrator Master", page_icon="🤖", layout="wide")

# ==================== SESSION STATE ====================
if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = MasterOrchestrator(name="master_dashboard")
if "ingestion_agent" not in st.session_state:
    st.session_state.ingestion_agent = IngestionAgent(use_intelligent_rbac=True)
if "retrieval_agent" not in st.session_state:
    st.session_state.retrieval_agent = RetrievalAgent(use_intelligent_rbac=True)
if "healing_agent" not in st.session_state:
    st.session_state.healing_agent = HealingAgent(use_intelligent_rbac=True)
if "spawned_agents" not in st.session_state:
    st.session_state.spawned_agents = {}
if "ingestion_logs" not in st.session_state:
    st.session_state.ingestion_logs = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_task" not in st.session_state:
    st.session_state.current_task = None
if "current_file" not in st.session_state:
    st.session_state.current_file = None
if "current_database" not in st.session_state:
    st.session_state.current_database = None

orch = st.session_state.orchestrator
ingest_agent = st.session_state.ingestion_agent
retrieve_agent = st.session_state.retrieval_agent
heal_agent = st.session_state.healing_agent
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

def render_cot_reasoning(execution_log):
    """
    Render chain-of-thought reasoning loop in visual format.
    Similar to ChatGPT/Claude thinking display.
    """
    st.markdown("### 🧠 Reasoning Loop")
    
    if not execution_log:
        st.info("No reasoning trace available")
        return
    
    # Extract COT steps from execution log
    cot_steps = []
    current_iteration = 0
    current_phase = None
    current_output = None
    
    for entry in execution_log:
        if "steps" in entry:
            for step in entry["steps"]:
                phase = step.get("phase", "")
                output = step.get("output", {})
                
                if phase in ["think", "evaluate", "rethink"]:
                    cot_steps.append({
                        "phase": phase,
                        "output": output,
                        "iteration": current_iteration if phase == "rethink" else 0
                    })
                    
                    if phase == "rethink":
                        current_iteration += 1
    
    if not cot_steps:
        st.info("No chain-of-thought steps recorded")
        return
    
    # Display reasoning in expandable sections
    with st.container():
        # Create columns for phase overview
        phase_cols = st.columns(3)
        
        think_count = len([s for s in cot_steps if s["phase"] == "think"])
        eval_count = len([s for s in cot_steps if s["phase"] == "evaluate"])
        rethink_count = len([s for s in cot_steps if s["phase"] == "rethink"])
        
        with phase_cols[0]:
            st.metric("🤔 Think", think_count, "phases")
        with phase_cols[1]:
            st.metric("✅ Evaluate", eval_count, "phases")
        with phase_cols[2]:
            st.metric("🔄 Rethink", rethink_count, "iterations")
        
        st.markdown("---")
        
        # Display iterative reasoning loop
        st.markdown("#### Iterative Reasoning Process:")
        
        iteration_data = {}
        for step in cot_steps:
            phase = step["phase"]
            iteration = step["iteration"]
            
            if iteration not in iteration_data:
                iteration_data[iteration] = {}
            iteration_data[iteration][phase] = step["output"]
        
        # Show each iteration
        for iteration in sorted(iteration_data.keys()):
            phases_in_iter = iteration_data[iteration]
            
            if iteration == 0:
                header = "📍 **Initial Analysis Phase**"
            else:
                header = f"🔁 **Iteration {iteration}**"
            
            with st.expander(header, expanded=(iteration == 0)):
                # THINK phase
                if "think" in phases_in_iter:
                    with st.container():
                        st.markdown("##### 🤔 THINK - Analysis & Planning")
                        think_output = phases_in_iter["think"]
                        
                        if isinstance(think_output, dict):
                            for key, value in think_output.items():
                                if key != "phase":
                                    st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
                        else:
                            st.markdown(f"{think_output}")
                        
                        st.markdown("---")
                
                # EVALUATE phase
                if "evaluate" in phases_in_iter:
                    with st.container():
                        st.markdown("##### ✅ EVALUATE - Assess & Score")
                        eval_output = phases_in_iter["evaluate"]
                        
                        if isinstance(eval_output, dict):
                            # Show score as visual progress
                            if "score" in eval_output:
                                score = eval_output.get("score", 0)
                                st.progress(min(score, 1.0))
                                st.markdown(f"**Score:** {score:.2f}/1.0")
                            
                            # Show feedback
                            if "feedback" in eval_output:
                                st.markdown(f"**Feedback:** {eval_output['feedback']}")
                            
                            # Show other details
                            for key, value in eval_output.items():
                                if key not in ["score", "feedback", "phase"]:
                                    st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
                        else:
                            st.markdown(f"{eval_output}")
                        
                        st.markdown("---")
                
                # RETHINK phase
                if "rethink" in phases_in_iter:
                    with st.container():
                        st.markdown("##### 🔄 RETHINK - Refine & Improve")
                        rethink_output = phases_in_iter["rethink"]
                        
                        if isinstance(rethink_output, dict):
                            for key, value in rethink_output.items():
                                if key != "phase":
                                    st.markdown(f"- **{key.replace('_', ' ').title()}:** {value}")
                        else:
                            st.markdown(f"{rethink_output}")

def render_agent_execution_details(agents_used, execution_log):
    """Render detailed execution information for each agent."""
    st.markdown("### 🤖 Agent Execution Details")
    
    with st.expander("View Agent Logs", expanded=False):
        # execution_log should be list of COT logs from agents
        if not execution_log or not isinstance(execution_log, list):
            st.info("No execution logs available")
            return
        
        for entry in execution_log:
            if not isinstance(entry, dict):
                continue
            
            agent_name = entry.get("agent", "Unknown Agent")
            status = entry.get("status", "pending")
            
            status_emoji = {
                "success": "✅",
                "error": "❌",
                "pending": "⏳",
                "running": "🔄"
            }.get(status, "❓")
            
            with st.expander(f"{status_emoji} {agent_name}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Agent ID:** `{entry.get('agent_id', 'N/A')[:8]}...`")
                    st.markdown(f"**Status:** {status}")
                    st.markdown(f"**COT Enabled:** {entry.get('cot_enabled', True)}")
                
                with col2:
                    timestamp = entry.get("timestamp", "")
                    st.markdown(f"**Timestamp:** {timestamp}")
                    spawned = entry.get("spawned_agents", [])
                    st.markdown(f"**Spawned Agents:** {len(spawned)}")
                
                if "steps" in entry and entry["steps"]:
                    st.markdown("**COT Steps:**")
                    for i, step in enumerate(entry["steps"], 1):
                        phase = step.get("phase", "unknown")
                        iteration = step.get("iteration", 0)
                        output = step.get("output", {})
                        
                        # Display step with details
                        step_header = f"{i}. **{phase.upper()}**"
                        if iteration > 0:
                            step_header += f" (Iteration {iteration})"
                        
                        st.markdown(step_header)
                        
                        if isinstance(output, dict):
                            for key, value in list(output.items())[:3]:  # Show top 3 fields
                                st.markdown(f"   - {key}: {value}")
                        else:
                            st.markdown(f"   - {output}")
                
                if "error" in entry:
                    st.error(f"Error: {entry['error']}")

# ==================== SIDEBAR ====================
st.sidebar.title("🤖 ORCHESTRATOR MASTER")
st.sidebar.markdown("**Master Control Center with LangChain DeepAgents**")

page = st.sidebar.radio("Navigation", [
    "🎯 Orchestrator Pool",
    "📊 Summary",
    "🔄 Simulation",
    "📥 Ingest",
    "🔍 Retrieve",
    "🧹 Heal",
    "⚙️ System"
])

st.sidebar.markdown("---")
st.sidebar.subheader("📊 System")
c1, c2 = st.sidebar.columns(2)
c1.metric("Docs", stats.get('total_documents', 0))
c2.metric("Queries", stats.get('queries_24h', 0))
c1.metric("Agents", stats.get('active_agents', 0))
c2.metric("Time", f"{stats.get('avg_response_time', 0):.1f}s")

# ==================== PAGE 1: ORCHESTRATOR POOL (CHATBOT) ====================
if page == "🎯 Orchestrator Pool":
    st.title("🤖 RAG Agent Chatbot")
    st.markdown("**Chat with agents | Type 'hi', 'help', or your question | Select an option**")
    
    # ==================== CHATBOT INTERFACE ====================
    
    # Display chat history
    st.subheader("💬 Conversation")
    
    chat_container = st.container()
    
    with chat_container:
        # Show previous messages
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])
    
    # ==================== USER INPUT ====================
    st.markdown("---")
    
    user_input = st.text_input(
        "You:",
        placeholder="Type 'hi', 'hello', 'help' or ask a question...",
        key="user_input_main"
    )
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Process user input
        user_input_lower = user_input.lower().strip()
        
        # Detect intent
        if user_input_lower in ["hi", "hello", "hey", "help", "start", "begin"]:
            # Show options for what user wants to do
            response = """
            👋 **Welcome to RAG Agent System!**
            
            What would you like to do? Please choose one of these options:
            
            1️⃣ **INGEST** - Upload and process documents from folders
            2️⃣ **RETRIEVE** - Search and find information in the knowledge base
            3️⃣ **HEAL** - Optimize and repair the vector database
            
            You can also:
            - Type **'ingest'** to upload documents
            - Type **'retrieve'** to search information
            - Type **'heal'** to optimize the system
            - Type **'clear'** to clear chat history
            """
            option_selected = None
        
        else:
            # Detect action from user input
            routing = st.session_state.orchestrator.route_command(user_input)
            intent = routing.get("intent")
            
            if intent == "ingest":
                response = f"""
                ✅ **Detected: INGEST MODE**
                
                I'll help you upload and process documents.
                
                What folder would you like to ingest from?
                - 📘 Engineering Docs
                - 📗 HR Documents  
                - 📙 General Docs
                - 📊 CSV Sources
                - 📑 JSON Sources
                
                Or just type the folder name to proceed.
                """
                st.session_state.current_task = "ingest"
            
            elif intent == "retrieve":
                response = f"""
                ✅ **Detected: RETRIEVE MODE**
                
                I'll search for information in the knowledge base.
                
                **Your query:** "{user_input}"
                
                What role are you? (for access control)
                - 👨‍💼 Engineer (access level 3)
                - 👩‍💼 HR Manager (access level 2)
                - 🔑 Admin (access level 5)
                
                Or just say your role to retrieve results!
                """
                st.session_state.current_task = "retrieve"
            
            elif intent == "heal":
                response = f"""
                ✅ **Detected: HEAL MODE**
                
                I'll optimize the vector database.
                
                What healing mode?
                - 🔧 Full - Complete optimization
                - 📦 Namespace - Fix specific namespace
                - 🧩 Chunk - Rebuild chunk metadata
                - 📈 Embedding - Regenerate embeddings
                
                Or just say the mode!
                """
                st.session_state.current_task = "heal"
            
            else:
                response = f"""
                ❓ **I didn't understand that action.**
                
                Please choose one of these:
                1️⃣ **Type 'ingest'** - to upload documents
                2️⃣ **Type 'retrieve'** - to search information  
                3️⃣ **Type 'heal'** - to optimize system
                
                Or ask me something and I'll try to figure it out!
                """
        
        # Add assistant response to history
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        # Show options as buttons
        st.markdown("---")
        st.subheader("🎯 Quick Actions")
        
        col_opt1, col_opt2, col_opt3 = st.columns(3)
        
        with col_opt1:
            if st.button("📥 INGEST", key="btn_ingest", use_container_width=True):
                st.session_state.current_task = "ingest"
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": "✅ **Ingest Mode Activated** - Select a folder and file to upload"
                })
                st.rerun()
        
        with col_opt2:
            if st.button("🔍 RETRIEVE", key="btn_retrieve", use_container_width=True):
                st.session_state.current_task = "retrieve"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "✅ **Retrieve Mode Activated** - Enter your search query"
                })
                st.rerun()
        
        with col_opt3:
            if st.button("🧹 HEAL", key="btn_heal", use_container_width=True):
                st.session_state.current_task = "heal"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": "✅ **Heal Mode Activated** - System optimization started"
                })
                st.rerun()
        
        col_opt4, col_opt5 = st.columns(2)
        
        with col_opt4:
            if st.button("🗑️ Clear Chat", key="btn_clear", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.current_task = None
                st.rerun()
        
        with col_opt5:
            if st.button("ℹ️ Help", key="btn_help", use_container_width=True):
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": """
                    📚 **RAG System Help:**
                    
                    **INGEST** - Add documents to knowledge base
                    - Select folder (Engineering, HR, General, CSV, JSON)
                    - Choose file
                    - System processes: Chunking → Metadata → RBAC → Embeddings → Storage
                    
                    **RETRIEVE** - Search knowledge base
                    - Enter query
                    - Select user role (Engineer/HR/Admin)
                    - System searches and returns relevant documents
                    
                    **HEAL** - Maintain the system
                    - Optimize vector store
                    - Rebuild indexes
                    - Fix corrupted embeddings
                    """
                })
                st.rerun()
    
    # ==================== TASK-SPECIFIC INTERFACE ====================
    
    if st.session_state.current_task == "ingest":
        st.markdown("---")
        st.subheader("📥 INGEST MODE - Upload Documents")
        
        col_ingest1, col_ingest2 = st.columns([1, 2])
        
        with col_ingest1:
            st.write("**Select Folder:**")
            folder_options = {
                "📘 Engineering Docs": "data/test_sources/engineering",
                "📗 HR Documents": "data/test_sources/hr",
                "📙 General Docs": "data/test_sources/general",
                "📊 CSV Sources": "data/test_sources/csv_sources",
                "📑 JSON Sources": "data/test_sources/json_sources",
            }
            selected_folder = st.selectbox("Choose folder:", list(folder_options.keys()), label_visibility="collapsed")
            folder_path = folder_options[selected_folder]
        
        with col_ingest2:
            st.write("**Select File:**")
            import glob
            try:
                files_in_folder = []
                for ext in ["*.txt", "*.csv", "*.json", "*.pdf", "*.md"]:
                    files_in_folder.extend(glob.glob(f"{folder_path}/{ext}"))
                    files_in_folder.extend(glob.glob(f"{folder_path}/*/{ext}"))
                
                if files_in_folder:
                    selected_file = st.selectbox("Choose file:", files_in_folder, label_visibility="collapsed")
                else:
                    st.warning("No files found")
                    selected_file = None
            except Exception as e:
                st.error(f"Error: {str(e)}")
                selected_file = None
        
        if selected_file:
            # Show file preview
            st.write("**File Preview:**")
            try:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                st.text_area("Content:", content[:500] + "..." if len(content) > 500 else content, height=150, disabled=True)
                
                # Ingest button
                if st.button("✅ Ingest This File", use_container_width=True, key="confirm_ingest"):
                    with st.spinner("Ingesting document..."):
                        try:
                            doc = Document(
                                id=f"doc_{selected_file.split('/')[-1].replace('.', '_')}",
                                content=content,
                                title=selected_file.split('/')[-1],
                                source=selected_folder,
                                metadata={"filename": selected_file}
                            )
                            
                            result = st.session_state.ingestion_agent.execute([doc])
                            
                            st.success(f"✅ Successfully ingested document! ({len(result)} document(s))")
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": f"✅ Ingested **{selected_file.split('/')[-1]}** successfully!"
                            })
                            st.session_state.current_task = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    elif st.session_state.current_task == "retrieve":
        st.markdown("---")
        st.subheader("🔍 RETRIEVE MODE - Search Knowledge Base")
        
        col_ret1, col_ret2 = st.columns([2, 1])
        
        with col_ret1:
            query = st.text_input("Enter your search query:", placeholder="e.g., database rollback procedure")
        
        with col_ret2:
            role = st.selectbox("Your Role (for RBAC):", ["engineer", "hr_manager", "admin"], label_visibility="collapsed")
        
        if query:
            access_levels = {"engineer": 3, "hr_manager": 2, "admin": 5}
            access_level = access_levels.get(role, 3)
            
            if st.button("🔍 Search", use_container_width=True, key="confirm_retrieve"):
                with st.spinner(f"Searching as {role}..."):
                    try:
                        user_data = {"id": 1, "role": role, "access_level": access_level}
                        result = st.session_state.retrieval_agent.execute(query, user_data)
                        
                        count = result.get('count', 0)
                        st.success(f"✅ Found {count} documents")
                        
                        if count > 0:
                            st.json(result)
                        else:
                            st.warning("No documents found matching your query")
                        
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": f"✅ Search complete! Found **{count}** documents for query: **'{query}'**"
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    elif st.session_state.current_task == "heal":
        st.markdown("---")
        st.subheader("🧹 HEAL MODE - System Optimization")
        
        col_heal1, col_heal2 = st.columns(2)
        
        with col_heal1:
            heal_mode = st.selectbox(
                "Select healing mode:",
                ["full", "namespace", "chunk", "embedding"],
                format_func=lambda x: {"full": "🔧 Full Optimization", "namespace": "📦 Namespace", 
                                       "chunk": "🧩 Chunk", "embedding": "📈 Embedding"}[x],
                label_visibility="collapsed"
            )
        
        with col_heal2:
            time_range = st.selectbox(
                "Time range:",
                ["24h", "7d", "30d", "all"],
                label_visibility="collapsed"
            )
        
        if st.button("▶️ Start Healing", use_container_width=True, key="confirm_heal"):
            with st.spinner(f"Running {heal_mode} healing..."):
                try:
                    result = st.session_state.healing_agent.execute(time_range=time_range, healing_mode=heal_mode)
                    
                    st.success("✅ Healing completed!")
                    st.json(result)
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"✅ Healing complete! Mode: **{heal_mode}** | Time range: **{time_range}**"
                    })
                    st.session_state.current_task = None
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # ==================== AGENT STATUS ====================
    st.markdown("---")
    st.subheader("📊 System Status")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    
    with col_s1:
        st.metric("Ingestion", "✅ Ready")
    with col_s2:
        st.metric("Retrieval", "✅ Ready")
    with col_s3:
        st.metric("Healing", "✅ Ready")
    with col_s4:
        st.metric("Chat Mode", "✅ Active")

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
            
            # NEW: Display full chain-of-thought reasoning loop
            st.markdown("---")
            cot_logs = execution_log.get("agents_cot_logs", [])
            render_cot_reasoning(cot_logs)
            
            # NEW: Display agent execution details
            st.markdown("---")
            render_agent_execution_details(agents_used, cot_logs)
            
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
    col1.metric("Total Documents", stats.get('total_documents', 0))
    col2.metric("Queries (24h)", stats.get('queries_24h', 0))
    col3.metric("Active Agents", stats.get('active_agents', 0))

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
    st.title("📥 Ingestion Workflow with Agent Pool")
    st.markdown("**Intelligent document ingestion with RBAC-aware namespace resolution**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        doc_source = st.selectbox("Select Source:", [
            "incident_knowledge", "engineering_docs", 
            "hr_policies", "sales_data", "test_data"
        ])
    with col2:
        doc_format = st.selectbox("Format:", ["txt", "json", "csv", "pdf"])
    with col3:
        department = st.selectbox("Department:", ["engineering", "hr", "sales", "general"])
    
    if st.button("📥 Ingest & Spawn Agents"):
        agents = spawn_agents("ingest")
        st.session_state.spawned_agents["current"] = agents
        
        st.markdown("---")
        st.subheader("🤖 Ingestion Agent Pool")
        render_agent_pool(agents)
        
        st.markdown("---")
        with st.spinner("Ingesting documents through agent pipeline..."):
            try:
                # Call ingestion agent with RBAC support
                result = ingest_agent.execute(
                    source=doc_source,
                    format_type=doc_format,
                    department=department,
                    use_intelligent_rbac=True
                )
                
                st.success("✅ Ingestion Complete!")
                
                st.markdown("---")
                st.subheader("📊 Ingestion Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Documents Ingested", result.get("documents_ingested", 0))
                col2.metric("Chunks Created", result.get("chunks_created", 0))
                col3.metric("Namespace", result.get("namespace", "unknown"))
                col4.metric("Status", "✅ Success")
                
                st.markdown("---")
                st.subheader("🔗 Agent Execution Chain")
                agent_names = ["DataLoader", "Detector", "Classifier", "Chunker"]
                cols = st.columns(len(agent_names))
                for i, col in enumerate(cols):
                    with col:
                        st.markdown(f"**{i+1}. {agent_names[i]}**")
                        st.markdown("✓ Complete")
                
                st.markdown("---")
                st.subheader("🧠 COT Reasoning Trace")
                
                if result.get("cot_log"):
                    cot_steps = result.get("cot_log", [])
                    for i, step in enumerate(cot_steps[:5], 1):
                        st.markdown(f"**Step {i}:** {step}")
                else:
                    st.info("No reasoning trace available")
                
                st.markdown("---")
                st.subheader("📄 Ingested Documents")
                
                if result.get("documents"):
                    df_docs = pd.DataFrame([
                        {
                            "Document": doc.get("name", "Unknown")[:30],
                            "Namespace": doc.get("namespace", "N/A"),
                            "Chunks": doc.get("chunk_count", 0),
                            "Size": f"{doc.get('size', 0)} bytes"
                        }
                        for doc in result.get("documents", [])[:5]
                    ])
                    st.dataframe(df_docs, width='stretch')
                else:
                    st.info("No documents ingested")
                    
            except Exception as e:
                st.error(f"❌ Ingestion Error: {str(e)}")
                st.info("Make sure the orchestrator is properly initialized")


# ==================== PAGE 5.5: HEALING ====================
elif page == "🧹 Heal":
    st.title("🧹 Vector Store Healing & Optimization")
    st.markdown("**Intelligent namespace fragmentation analysis and optimization**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        namespace = st.selectbox("Select Namespace:", [
            "technical", "process", "policy", 
            "knowledge", "incident", "data", "personal"
        ])
    with col2:
        healing_mode = st.selectbox("Healing Mode:", [
            "full", "namespace", "chunk", "refragment", "status"
        ])
    with col3:
        department = st.selectbox("Department:", ["engineering", "hr", "sales", "general", "all"])
    
    if st.button("🧹 Analyze & Heal"):
        agents = spawn_agents("heal")
        st.session_state.spawned_agents["current"] = agents
        
        st.markdown("---")
        st.subheader("🤖 Healing Agent Pool")
        render_agent_pool(agents)
        
        st.markdown("---")
        with st.spinner("Analyzing namespace and executing healing operations..."):
            try:
                # Call healing agent
                result = heal_agent.execute(
                    namespace=namespace,
                    healing_mode=healing_mode,
                    department=department,
                    use_intelligent_rbac=True
                )
                
                st.success("✅ Healing Complete!")
                
                st.markdown("---")
                st.subheader("📊 Healing Summary")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Namespace", namespace)
                col2.metric("Documents Analyzed", result.get("documents_analyzed", 0))
                col3.metric("Issues Found", result.get("issues_found", 0))
                col4.metric("Healed", result.get("healed_count", 0))
                
                st.markdown("---")
                st.subheader("🔗 Agent Execution Chain")
                agent_names = ["Analyzer", "Optimizer", "Cleaner"]
                cols = st.columns(len(agent_names))
                for i, col in enumerate(cols):
                    with col:
                        st.markdown(f"**{i+1}. {agent_names[i]}**")
                        st.markdown("✓ Complete")
                
                st.markdown("---")
                st.subheader("📈 Before & After Metrics")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Before Healing:**")
                    if result.get("before_metrics"):
                        before = result["before_metrics"]
                        st.metric("Fragment Count", before.get("fragment_count", 0))
                        st.metric("Avg Fragment Size", f"{before.get('avg_size', 0)} bytes")
                        st.metric("Health Score", f"{before.get('health_score', 0):.2f}")
                
                with col2:
                    st.markdown("**After Healing:**")
                    if result.get("after_metrics"):
                        after = result["after_metrics"]
                        st.metric("Fragment Count", after.get("fragment_count", 0))
                        st.metric("Avg Fragment Size", f"{after.get('avg_size', 0)} bytes")
                        st.metric("Health Score", f"{after.get('health_score', 0):.2f}")
                
                st.markdown("---")
                st.subheader("🧠 COT Reasoning Trace")
                
                if result.get("cot_log"):
                    for i, step in enumerate(result.get("cot_log", [])[:5], 1):
                        st.markdown(f"**Step {i}:** {step}")
                else:
                    st.info("No reasoning trace available")
                
                st.markdown("---")
                st.subheader("🔧 Healing Actions Performed")
                
                if result.get("actions"):
                    for i, action in enumerate(result.get("actions", []), 1):
                        st.markdown(f"**{i}. {action}**")
                else:
                    st.info("No actions performed")
                
                st.markdown("---")
                st.subheader("💡 Recommendations")
                
                if result.get("recommendations"):
                    for rec in result.get("recommendations", []):
                        st.info(rec)
                else:
                    st.success("✅ No further recommendations")
                    
            except Exception as e:
                st.error(f"❌ Healing Error: {str(e)}")
                st.info("Make sure the healing agent is properly initialized")


# ==================== PAGE 6: SYSTEM ====================
elif page == "⚙️ System":
    st.title("⚙️ System Configuration")
    configs = {"System": "config/system_config.yaml"}
    selected = st.selectbox("Config:", list(configs.keys()))
    st.info(f"Configuration: {selected}")

st.markdown("---")
st.markdown(f"🤖 RAG Orchestrator Master | LangChain DeepAgents | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
