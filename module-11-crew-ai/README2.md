# CrewAI Multi-Agent System

A sophisticated multi-agent orchestration system for complex AI workflows, demonstrating advanced agentic AI patterns and local LLM integration.

## 🎯 Overview

The CrewAI module provides a complete multi-agent system that orchestrates specialized agents to accomplish complex tasks through coordinated workflows. It serves as Module 11 of the SnapAudit AI Engineering Fellowship, showcasing advanced agentic AI patterns.

## 🏗️ Architecture

### Core Components

- **Agent System**: Modular agent architecture with role-based capabilities
- **Crew Orchestration**: Dynamic workflow coordination and execution
- **Tool Integration**: Seamless integration with external APIs and services
- **Ollama Integration**: Local LLM deployment with configurable models
- **RAG Integration**: Hybrid retrieval from module-3 systems
- **Streamlit Interface**: Interactive testing and demonstration platform

### Agent Types

1. **Retriever Agent**: Searches and retrieves relevant policy information
2. **Summarizer Agent**: Generates summaries and insights from retrieved data  
3. **Logger Agent**: Tracks and logs all workflow activities

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+**
- **Ollama** (for local AI models)
- **Environment variables** configured in `.env` file

### Installation

```bash
# The CrewAI module is part of the main project
# No additional installation required
```

### Configuration

Create a `.env` file in the project root:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:latest
OLLAMA_EMBED_MODEL=embeddinggemma:latest

# Optional: OpenAI for fallback
OPENAI_API_KEY=your_openai_api_key_here
```

### Running the System

```bash
# Interactive Streamlit interface
uv run py -m streamlit run crew-ai/streamlit_app.py

# Command line demo
uv run crew-ai/run_demo.py

# Integration tests
uv run crew-ai/test_integration.py

# Ollama API testing
uv run ollama_test.py
```

## 📊 Features

### Multi-Agent Capabilities

- **Dynamic Crew Building**: Runtime agent configuration and assembly
- **Flexible Workflows**: Customizable agent sequences and logic
- **Tool Integration**: External API and service integration
- **Real-time Logging**: Comprehensive execution tracking and monitoring
- **Error Handling**: Graceful failure recovery and fallbacks
- **Performance Monitoring**: Execution metrics and timing

### Agent Architecture

- **Retriever Agent**: Policy information retrieval and search
- **Summarizer Agent**: Text generation and summarization
- **Logger Agent**: Activity tracking and audit logging
- **Tool System**: Extensible tool framework

### Integration Features

- **Module-3 RAG**: Hybrid retrieval system integration
- **Ollama Models**: Support for multiple local models
- **Environment Config**: Flexible configuration management
- **Session State**: Streamlit state persistence
- **JSON Handling**: Robust response parsing and display

## 🛠️ Development

### Module Structure

```
crew-ai/
├── __init__.py          # Package initialization
├── agents.py            # Agent definitions and classes
├── tools.py             # Tool implementations and integrations
├── crew.py              # Crew orchestration and workflow
├── run_demo.py          # Demo and testing functions
├── streamlit_app.py     # Interactive web interface
├── test_integration.py  # Integration testing
├── ollama_test.py       # Ollama API testing
├── .env.example          # Environment configuration template
└── README.md            # Module documentation
```

### Key Classes

- **Agent**: Base agent class with role-based capabilities
- **RetrieverTool**: Tool for RAG system integration
- **OllamaGenerator**: Local LLM interface and management
- **Crew**: Multi-agent orchestration and workflow execution

### Usage Examples

```python
from crew_ai.run_demo import build_demo_crew, demo_run
from crew_ai.agents import Agent
from crew_ai.tools import RetrieverTool, OllamaGenerator

# Build a custom crew
crew = build_demo_crew(hybrid_retriever)

# Run a workflow
results = demo_run(hybrid_retriever, "What is the daily per diem limit?")

# Custom agent creation
agent = Agent(name="custom", role="specialist", tools={})
```

## 🧪 Testing

### Test Suites

```bash
# Run integration tests
uv run crew-ai/test_integration.py

# Test Ollama connectivity
uv run ollama_test.py

# Test individual components
uv run crew-ai/run_demo.py
```

### Test Coverage

- **Agent Creation**: Verify agent initialization and configuration
- **Tool Integration**: Test external API connections
- **Crew Orchestration**: Validate workflow execution
- **Ollama Integration**: Confirm LLM functionality
- **Error Handling**: Test failure scenarios and recovery
- **Performance**: Monitor execution time and resource usage

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|-----------|----------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `gemma3:latest` | Primary generation model |
| `OLLAMA_EMBED_MODEL` | `embeddinggemma:latest` | Embedding model |
| `OPENAI_API_KEY` | `None` | Optional OpenAI fallback |

### Model Support

- **gemma3:latest** - Primary generation model
- **embeddinggemma:latest** - Embedding generation
- **qwen3:8b** - Alternative generation model
- **llama3.1:latest** - Alternative generation model

## 🚀 Advanced Features

### Workflow Customization

```python
# Define custom workflows
workflow = [
    {"agent": "retriever", "action": "retrieve", "input": {"query": "custom query"}},
    {"agent": "summarizer", "action": "generate", "input": {"prompt": "custom prompt"}},
    {"agent": "logger", "action": "log", "input": {"message": "custom log"}}
]

# Execute with crew
results = crew.run_workflow(workflow)
```

### Error Handling

- **Connection Failures**: Automatic retry and fallback mechanisms
- **Model Unavailability**: Graceful degradation when models unavailable
- **Invalid Responses**: Robust JSON parsing and error recovery
- **Resource Limits**: Timeout and memory management
- **Logging**: Comprehensive error tracking and debugging

## 📈 Performance

### Optimization Features

- **Local LLM Priority**: Prefer local models for privacy and speed
- **Semantic Caching**: Reduce redundant API calls
- **Batch Processing**: Optimize multiple request handling
- **Resource Monitoring**: Track memory and CPU usage
- **Response Caching**: Cache frequently used responses

## 🔒 Security

### Safety Measures

- **Input Validation**: Sanitize all user inputs and prompts
- **Content Filtering**: Built-in content moderation
- **Access Control**: Role-based agent permissions
- **Audit Logging**: Complete activity tracking
- **Error Boundaries**: Secure error message handling

## 🎯 Use Cases

### Expense Auditing

- **Policy Retrieval**: Find relevant expense policies
- **Compliance Checking**: Validate expenses against rules
- **Report Generation**: Create audit summaries
- **Decision Support**: Assist with complex determinations

### Enterprise Integration

- **ERP Systems**: Connect to enterprise resource planning
- **Policy Databases**: Integrate with knowledge bases
- **Workflow Engines**: Orchestrate business processes
- **Notification Systems**: Send alerts and updates

## 🐛 Troubleshooting

### Common Issues

**Ollama Connection Failed**

```bash
# Check if Ollama is running
ollama list

# Restart Ollama
ollama serve

# Test connection
uv run ollama_test.py
```

**Module Import Errors**

```bash
# Check dependencies
uv sync

# Verify environment variables
cat .env

# Check logs
tail -f logs/*.log
```

**Performance Issues**

```bash
# Monitor resources
htop

# Check Ollama stats
docker stats

# Run performance tests
uv run crew-ai/test_integration.py
```

## 🤝 Contributing

### Development Workflow

1. **Fork** the repository
2. **Create** feature branch
3. **Implement** changes with tests
4. **Document** updates
5. **Submit** pull request

### Code Standards

- **Type Hints**: Use comprehensive type annotations
- **Docstrings**: Document all public functions and classes
- **Error Handling**: Implement robust exception management
- **Logging**: Use centralized logging configuration
- **Testing**: Write comprehensive unit and integration tests

## 📄 License

This module is part of the AI Engineering Fellowship and demonstrates advanced agentic AI patterns and multi-agent system design.

---

**🚀 Ready to build sophisticated multi-agent systems?**

The CrewAI module provides everything you need to create, orchestrate, and deploy advanced agentic AI workflows with local LLM integration!
