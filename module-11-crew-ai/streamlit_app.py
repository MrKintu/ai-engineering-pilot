"""
CrewAI Streamlit Demo Interface

Interactive Streamlit application for testing and demonstrating the CrewAI system
with SnapAudit integration. This app provides a user-friendly interface to:
- Configure and run CrewAI workflows
- Test individual agents and tools
- Monitor execution with real-time logging
- Visualize results and agent interactions
"""

import sys
import json
import time
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
from dotenv import load_dotenv

# Add project root to path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
sys.path.append(str(Path(__file__).resolve().parents[1] / "module-3-rag-systems"))

# Import centralized logging configuration
from logger_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

# Load environment variables from .env file in root directory
load_dotenv()
env = os.environ

# Ollama configuration from environment variables
OLLAMA_BASE_URL = env.get("OLLAMA_BASE_URL")
OLLAMA_EMBED_MODEL = env.get("OLLAMA_EMBED_MODEL")
OLLAMA_MODEL = env.get("OLLAMA_MODEL")

# Import CrewAI components
from agents import Agent
from tools import RetrieverTool, OllamaGenerator, logger_tool
from crew import Crew
from run_demo import build_demo_crew, demo_run, create_hybrid_retriever

# Import RAG retriever from module 3
try:
    from streamlit_app2 import HybridRetriever, DenseVectorRetriever, SparseBM25Retriever
    from streamlit_app2 import DocumentChunk, DocumentIngestionPipeline
    RAG_AVAILABLE = True
except ImportError as e:
    logger.warning(f"RAG components not available: {e}")
    RAG_AVAILABLE = False

# Configure Streamlit page
st.set_page_config(
    page_title="CrewAI Demo - SnapAudit",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.metric-container {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
}
.agent-card {
    background-color: #ffffff;
    padding: 1rem;
    border-radius: 0.5rem;
    border: 1px solid #e0e0e0;
    margin: 0.5rem 0;
}
.workflow-step {
    background-color: #f8f9fa;
    padding: 0.75rem;
    border-radius: 0.25rem;
    border-left: 4px solid #007bff;
    margin: 0.25rem 0;
}
</style>
""", unsafe_allow_html=True)


class MockRetriever:
    """Mock retriever for demo purposes when RAG is not available."""
    
    def __init__(self):
        self.name = "MockRetriever"
    
    def search(self, query: str, top_k: int = 5):
        """Return mock results for demonstration."""
        # Log the query for debugging (uses the parameter)
        logger.debug(f"MockRetriever searching for: '{query}' with top_k={top_k}")
        
        # Mock results based on common expense policy questions
        mock_results = [
            ("Daily per diem is $75 for meals and $150 for lodging.", 0.95),
            ("Receipts must be submitted within 30 days of travel.", 0.87),
            ("Alcohol expenses require manager approval.", 0.82),
            ("Client entertainment expenses are limited to $100 per person.", 0.78),
            ("Travel advances must be reconciled within 2 weeks.", 0.75),
        ]
        return mock_results[:top_k]


def initialize_session_state():
    """Initialize session state variables."""
    if 'crew' not in st.session_state:
        st.session_state.crew = None
    if 'retriever' not in st.session_state:
        st.session_state.retriever = None
    if 'workflow_results' not in st.session_state:
        st.session_state.workflow_results = {}
    if 'agent_logs' not in st.session_state:
        st.session_state.agent_logs = []
    if 'execution_history' not in st.session_state:
        st.session_state.execution_history = []
    # Add Ollama configuration to session state from environment variables
    if 'ollama_base_url' not in st.session_state:
        st.session_state.ollama_base_url = OLLAMA_BASE_URL
    if 'ollama_model' not in st.session_state:
        st.session_state.ollama_model = OLLAMA_MODEL


def setup_retriever() -> Optional[Any]:
    """Set up and return a retriever instance."""
    try:
        st.info("🔍 Setting up hybrid retriever...")
        
        # Use the create_hybrid_retriever function from run_demo
        retriever = create_hybrid_retriever()
        
        if hasattr(retriever, 'name') and retriever.name == "MockRetriever":
            st.warning("⚠️ Using mock retriever for demo (RAG components not available)")
        else:
            st.success("✅ Hybrid retriever initialized successfully!")
        
        return retriever
        
    except Exception as e:
        logger.error(f"Failed to setup retriever: {e}")
        st.error(f"❌ Failed to setup retriever: {e}")
        return MockRetriever()


def render_agent_info(agent: Agent) -> None:
    """Render information about an agent."""
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"**{agent.name}**")
            st.caption(f"Role: {agent.role}")
        
        with col2:
            st.metric("Tools", len(agent.tools))
        
        with col3:
            st.metric("Memory Items", len(agent.memory))
        
        if agent.tools:
            with st.expander(f"Available Tools for {agent.name}"):
                for tool_name in agent.tools.keys():
                    st.code(f"• {tool_name}")


def render_workflow_step(step: Dict[str, Any], step_num: int) -> None:
    """Render a single workflow step."""
    agent_name = step.get("agent", "Unknown")
    action = step.get("action", "Unknown")
    inputs = step.get("input", {})
    
    with st.container():
        st.markdown(f"""
        <div class="workflow-step">
            <strong>Step {step_num}:</strong> {agent_name} → {action}
        </div>
        """, unsafe_allow_html=True)
        
        if inputs:
            with st.expander(f"Step {step_num} Inputs"):
                st.json(inputs)


def render_execution_results(results: Dict[str, Any]) -> None:
    """Render the execution results."""
    if not results:
        st.info("No results to display")
        return
    
    st.subheader("📊 Execution Results")
    
    for agent_name, agent_results in results.items():
        with st.expander(f"🤖 {agent_name} Results"):
            for i, result in enumerate(agent_results):
                st.markdown(f"**Result {i+1}:**")
                
                # Handle different result types appropriately
                if isinstance(result, dict):
                    # Display structured data as JSON
                    st.json(result)
                elif isinstance(result, str):
                    # Display text results in a code block
                    st.code(result, language="text")
                elif result is None:
                    st.info("No result returned")
                else:
                    # Try to display as JSON, fallback to text
                    try:
                        st.json(result)
                    except (TypeError, ValueError):
                        st.code(str(result), language="text")


def render_agent_logs() -> None:
    """Render agent execution logs."""
    if not st.session_state.agent_logs:
        st.info("No agent logs available")
        return
    
    st.subheader("📝 Agent Logs")
    
    # Filter logs by agent
    selected_agent = st.selectbox(
        "Filter by Agent",
        ["All"] + list({log.get("agent", "Unknown") for log in st.session_state.agent_logs})
    )
    
    logs_to_show = st.session_state.agent_logs
    if selected_agent != "All":
        logs_to_show = [log for log in logs_to_show if log.get("agent") == selected_agent]
    
    for log in logs_to_show:
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                st.caption(log.get("timestamp", ""))
            
            with col2:
                st.code(f"{log.get('agent', 'Unknown')}: {log.get('message', '')}")
            
            with col3:
                level = log.get("level", "INFO")
                if level == "ERROR":
                    st.error(level)
                elif level == "WARNING":
                    st.warning(level)
                else:
                    st.info(level)


def render_sidebar():
    """Render the sidebar configuration section."""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Environment Configuration Display
        st.subheader("🌍 Environment Settings")
        st.caption("Loaded from .env file")
        st.code(f"""
OLLAMA_BASE_URL: {OLLAMA_BASE_URL}
OLLAMA_EMBED_MODEL: {OLLAMA_EMBED_MODEL}
OLLAMA_MODEL: {OLLAMA_MODEL}
        """, language="bash")
        
        # Ollama Configuration
        st.subheader("🦙 Ollama Settings")
        st.caption("Override environment settings")
        st.session_state.ollama_base_url = st.text_input(
            "Ollama Base URL",
            value=st.session_state.ollama_base_url,
            help="Base URL for Ollama API (overrides environment variable)"
        )
        st.session_state.ollama_model = st.text_input(
            "Ollama Model",
            value=st.session_state.ollama_model,
            help="Model to use for generation (overrides environment variable)"
        )
        
        # Setup buttons
        render_setup_buttons()


def render_setup_buttons():
    """Render the setup buttons for retriever and crew."""
    # Retriever Setup
    st.subheader("🔍 Retriever Setup")
    if st.button("Initialize Retriever", type="primary"):
        with st.spinner("Setting up retriever..."):
            st.session_state.retriever = setup_retriever()
            if st.session_state.retriever:
                st.success("✅ Retriever initialized successfully!")
    
    # Crew Setup
    st.subheader("👥 Crew Setup")
    if st.button("Initialize Crew", type="primary") and st.session_state.retriever:
        with st.spinner("Building crew..."):
            try:
                st.session_state.crew = build_demo_crew(
                    st.session_state.retriever,
                    st.session_state.ollama_base_url,
                    st.session_state.ollama_model
                )
                st.success("✅ Crew initialized successfully!")
            except Exception as e:
                st.error(f"❌ Failed to initialize crew: {e}")
    
    # Clear session
    if st.button("🗑️ Clear Session"):
        st.session_state.clear()
        initialize_session_state()
        st.rerun()


def check_prerequisites():
    """Check if required components are initialized."""
    if not st.session_state.retriever:
        st.warning("⚠️ Please initialize the retriever in the sidebar to begin.")
        return False
    
    if not st.session_state.crew:
        st.warning("⚠️ Please initialize the crew in the sidebar to begin.")
        return False
    
    return True


def render_demo_tab():
    """Render the demo tab content."""
    st.header("🎯 CrewAI Demo")
    
    # Demo question input
    question = st.text_area(
        "Enter your question about expense policies:",
        value="What is the daily per diem limit for meals?",
        height=100,
        help="This question will be processed by the CrewAI workflow"
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_demo_execution(question)
    
    with col2:
        render_component_testing(question)
    
    # Display results
    if st.session_state.workflow_results:
        render_execution_results(st.session_state.workflow_results)


def render_demo_execution(question: str):
    """Render the demo execution section."""
    if st.button("🚀 Run Demo", type="primary"):
        with st.spinner("Running CrewAI workflow..."):
            try:
                start_time = time.time()
                results = demo_run(
                    hybrid_retriever=st.session_state.retriever, 
                    question=question,
                    ollama_base_url=st.session_state.ollama_base_url,
                    ollama_model=st.session_state.ollama_model
                )
                execution_time = time.time() - start_time
                
                st.session_state.workflow_results = results
                st.session_state.execution_history.append({
                    "question": question,
                    "results": results,
                    "execution_time": execution_time,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                
                st.success(f"✅ Demo completed in {execution_time:.2f} seconds")
                
            except Exception as e:
                st.error(f"❌ Demo failed: {e}")
                logger.error(f"Demo execution failed: {e}")


def render_component_testing(question: str):
    """Render the component testing section."""
    if st.button("🧪 Test Individual Components"):
        st.info("Testing individual components...")
        
        # Test retriever
        try:
            retriever_results = st.session_state.retriever.search(question, top_k=3)
            st.success("✅ Retriever test successful")
            st.json(retriever_results)
        except Exception as e:
            st.error(f"❌ Retriever test failed: {e}")


def render_agents_tab():
    """Render the agents tab content."""
    st.header("👥 Agent Information")
    
    if st.session_state.crew:
        agents = st.session_state.crew.agents_by_name
        
        for agent_name, agent in agents.items():
            with st.container():
                render_agent_info(agent)
                st.divider()


def render_workflow_tab():
    """Render the workflow tab content."""
    st.header("🔄 Workflow Configuration")
    
    # Default workflow
    default_workflow = [
        {"agent": "retriever", "action": "retrieve", "input": {"query": "What is the daily per diem limit?", "top_k": 5}},
        {"agent": "summarizer", "action": "generate", "input": {"prompt": "Summarize the retrieved policy information"}},
        {"agent": "logger", "action": "log", "input": {"message": "Workflow completed"}}
    ]
    
    st.subheader("Current Workflow")
    
    # Allow workflow customization
    workflow_json = st.text_area(
        "Workflow Configuration (JSON)",
        value=json.dumps(default_workflow, indent=2),
        height=200,
        help="Modify the workflow steps as needed"
    )
    
    if st.button("🔄 Run Custom Workflow"):
        try:
            workflow = json.loads(workflow_json)
            with st.spinner("Running custom workflow..."):
                results = st.session_state.crew.run_workflow(workflow)
                st.session_state.workflow_results = results
                st.success("✅ Custom workflow completed!")
                render_execution_results(results)
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {e}")
        except Exception as e:
            st.error(f"❌ Workflow execution failed: {e}")
    
    # Display workflow steps
    try:
        workflow = json.loads(workflow_json)
        st.subheader("Workflow Steps")
        for i, step in enumerate(workflow):
            render_workflow_step(step, i + 1)
    except json.JSONDecodeError:
        pass


def render_logs_tab():
    """Render the logs tab content."""
    st.header("📝 Execution Logs")
    
    # Show execution history
    if st.session_state.execution_history:
        st.subheader("📈 Execution History")
        
        for i, execution in enumerate(reversed(st.session_state.execution_history[-5:])):
            with st.expander(f"Execution {len(st.session_state.execution_history) - i}: {execution['timestamp']}"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(execution['question'])
                with col2:
                    st.metric("Time", f"{execution['execution_time']:.2f}s")
    
    render_agent_logs()


def render_footer():
    """Render the footer section."""
    st.divider()
    st.markdown("""
    **CrewAI Demo Interface** - Interactive testing environment for SnapAudit CrewAI integration
    
    This interface demonstrates:
    - Multi-agent orchestration with CrewAI
    - Integration with RAG systems for policy retrieval
    - Ollama integration for local AI generation
    - Real-time logging and monitoring
    - Customizable workflow execution
    """)


def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.title("🤖 CrewAI Demo Interface")
    st.caption("Interactive testing and demonstration of CrewAI system for SnapAudit")
    
    # Render sidebar
    render_sidebar()
    
    # Check prerequisites
    if not check_prerequisites():
        return
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Demo", "👥 Agents", "🔄 Workflow", "📝 Logs"])
    
    with tab1:
        render_demo_tab()
    
    with tab2:
        render_agents_tab()
    
    with tab3:
        render_workflow_tab()
    
    with tab4:
        render_logs_tab()
    
    # Footer
    render_footer()


if __name__ == "__main__":
    main()
