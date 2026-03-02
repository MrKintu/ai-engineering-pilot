# CrewAI Module for SnapAudit

> 🤖 **Multi-agent orchestration system for SnapAudit integration**

## 🎯 Overview

The CrewAI module provides a lightweight, flexible multi-agent framework designed specifically for SnapAudit workflows. It demonstrates how to orchestrate multiple AI agents to work together on expense auditing tasks.

## 🏗️ Architecture

### **Core Components**

- **🤖 Agents** - Autonomous agents with specific roles and tools
- **🔧 Tools** - Reusable components for specific tasks (retrieval, generation, logging)
- **👥 Crew** - Orchestrator that manages agent workflows
- **🎮 Streamlit Interface** - Interactive testing and demonstration UI

### **Agent Types**

1. **Retriever Agent** - Fetches relevant policy information
2. **Summarizer Agent** - Processes and summarizes retrieved content
3. **Logger Agent** - Tracks and logs workflow execution

## 🚀 Quick Start

### **Prerequisites**

- Python 3.13+
- Ollama running locally
- Required Python dependencies

### **Installation**

```bash
# From project root
cd crew-ai

# Install dependencies (if not already installed)
uv sync

# Start Ollama (if not running)
ollama serve

# Pull required model
ollama pull gemma3
```

### **Run the Streamlit App**

```bash
# From project root
uv run streamlit run crew-ai/streamlit_app.py
```

## 📱 Streamlit Interface Features

### **🎯 Demo Tab**

- Interactive question input for policy queries
- One-click demo execution
- Individual component testing
- Real-time result display

### **👥 Agents Tab**

- View agent configurations
- Monitor agent capabilities
- Check available tools
- Track agent memory usage

### **🔄 Workflow Tab**

- Visualize workflow steps
- Customize workflow configurations
- Test custom workflows
- Monitor execution flow

### **📝 Logs Tab**

- Real-time execution logs
- Agent-specific log filtering
- Execution history tracking
- Performance metrics

## 🔧 Configuration

### **Environment Variables**

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3

# Optional: OpenAI (for some components)
OPENAI_API_KEY=your_openai_api_key_here
```

### **Streamlit Configuration**

The Streamlit app provides an intuitive sidebar for:

- **Ollama Settings**: Configure base URL and model
- **Retriever Setup**: Initialize RAG components
- **Crew Setup**: Build and configure agent teams
- **Session Management**: Clear and reset sessions

## 🛠️ Usage Examples

### **Basic Demo**

```python
from crew_ai.run_demo import demo_run
from crew_ai.tools import MockRetriever

# Create mock retriever for demo
retriever = MockRetriever()

# Run demo with a question
results = demo_run(retriever, "What is the daily per diem limit?")
print(results)
```

### **Custom Crew**

```python
from crew_ai.agents import Agent
from crew_ai.tools import RetrieverTool, OllamaGenerator
from crew_ai.crew import Crew

# Create custom agents
retriever_agent = Agent(
    name="retriever", 
    role="policy_retriever",
    tools={"retrieve": RetrieverTool(retriever)}
)

summarizer_agent = Agent(
    name="summarizer",
    role="policy_summarizer", 
    tools={"generate": OllamaGenerator()}
)

# Build crew
crew = Crew([retriever_agent, summarizer_agent])

# Run custom workflow
workflow = [
    {"agent": "retriever", "action": "retrieve", "input": {"query": "expense policy", "top_k": 5}},
    {"agent": "summarizer", "action": "generate", "input": {"prompt": "Summarize the policy"}}
]

results = crew.run_workflow(workflow)
```

## 🔍 Module Structure

```
crew-ai/
├── __init__.py              # Module initialization
├── agents.py               # Agent implementation
├── tools.py                # Tool implementations
├── crew.py                 # Crew orchestration
├── run_demo.py             # Demo functions
├── streamlit_app.py        # Interactive UI
└── README.md               # This file
```

### **File Descriptions**

- **`agents.py`** - Core Agent class with memory and tool calling
- **`tools.py`** - RetrieverTool, OllamaGenerator, and utility functions
- **`crew.py`** - Crew orchestration and workflow management
- **`run_demo.py`** - Demo setup and execution functions
- **`streamlit_app.py`** - Interactive web interface

## 🧪 Testing

### **Unit Tests**

```bash
# Test individual components
python -m pytest crew-ai/test_agents.py
python -m pytest crew-ai/test_tools.py
python -m pytest crew-ai/test_crew.py
```

### **Integration Tests**

```bash
# Test full workflow
python -m pytest crew-ai/test_integration.py
```

### **Manual Testing**

Use the Streamlit interface for interactive testing:

1. Run `uv run streamlit run crew-ai/streamlit_app.py`
2. Initialize retriever and crew in sidebar
3. Test with different questions and workflows
4. Monitor logs and results

## 📊 Logging

The CrewAI module uses centralized logging configuration:

- **Log Files**: `logs/crew_ai_*.log`
- **Console Output**: Real-time logging during execution
- **Structured Format**: Timestamp, module, level, message

### **Log Levels**

- **DEBUG**: Detailed operation tracking
- **INFO**: High-level operations and milestones
- **WARNING**: Non-critical issues
- **ERROR**: Failure conditions and exceptions

## 🔗 Integration with SnapAudit

### **Module 3 Integration**

- Uses RAG systems for policy retrieval
- Leverages existing document chunks and embeddings
- Compatible with both BM25 and vector search

### **Module 1 Integration**

- Can use semantic router for intent classification
- Supports Ollama-based routing
- Fallback to keyword matching

### **Ollama Integration**

- Local AI model deployment
- Privacy-preserving processing
- Cost-effective generation
- Configurable model selection

## 🚀 Advanced Features

### **Custom Agents**

```python
class CustomAgent(Agent):
    def __init__(self, name: str, role: str, tools: Dict[str, Callable] = None):
        super().__init__(name, role, tools)
        self.custom_data = {}
    
    def custom_action(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Implement custom logic
        return {"result": "custom_output"}
```

### **Dynamic Workflows**

```python
# Build workflow dynamically
workflow = []

if query_type == "policy":
    workflow.append({"agent": "retriever", "action": "retrieve", "input": {"query": query}})
elif query_type == "summary":
    workflow.append({"agent": "summarizer", "action": "generate", "input": {"prompt": query}})

# Execute dynamic workflow
results = crew.run_workflow(workflow)
```

### **Tool Composition**

```python
# Combine multiple tools
combined_tool = CombinedTool([
    RetrieverTool(retriever),
    OllamaGenerator(),
    LoggerTool()
])

agent = Agent(
    name="multi_tool_agent",
    role="multi_task_agent",
    tools={"combined": combined_tool}
)
```

## 🐛 Troubleshooting

### **Common Issues**

**1. Ollama Connection Failed**

```bash
# Check Ollama status
ollama list

# Restart Ollama
ollama serve
```

**2. RAG Components Missing**

- The app uses mock retriever when RAG is unavailable
- Install module-3-rag-systems dependencies
- Check environment variables

**3. Agent Initialization Failed**

- Verify tool implementations
- Check import statements
- Review logging output

### **Debug Mode**

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

### **Adding New Agents**

1. Create agent class in `agents.py`
2. Implement required tools in `tools.py`
3. Update Streamlit interface
4. Add tests and documentation

### **Adding New Tools**

1. Implement tool class in `tools.py`
2. Add to agent configurations
3. Update demo workflows
4. Test integration

## 📈 Performance

### **Optimization Tips**

- Use semantic caching for repeated queries
- Batch multiple requests when possible
- Monitor token usage and costs
- Configure appropriate timeout values

### **Monitoring**

- Track execution time in Streamlit
- Monitor log file sizes
- Check agent memory usage
- Review workflow completion rates

## 🎓 Learning Objectives

This module demonstrates:

- **Multi-agent Systems**: Coordinating multiple AI agents
- **Tool Integration**: Combining different AI capabilities
- **Workflow Orchestration**: Managing complex execution flows
- **Interactive Interfaces**: Building user-friendly AI tools
- **Logging & Monitoring**: Production-ready observability

---

**🚀 Ready to explore multi-agent AI systems?**

Start the Streamlit app and begin experimenting with CrewAI workflows!
