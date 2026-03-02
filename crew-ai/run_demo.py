"""
Demo script that wires a RetrieverAgent + SummarizerAgent into a Crew,
using your Module 3 RAG retriever and Ollama generator.
Adjust imports to point to your actual retriever implementation.
"""
import sys
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Import centralized logging configuration
sys.path.append(str(Path(__file__).resolve().parents[1]))
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

from agents import Agent
from tools import RetrieverTool, OllamaGenerator, logger_tool
from crew import Crew

# Import hybrid retriever from module-3-rag-systems
try:
    from module_3_rag_systems.streamlit_app2 import (
        HybridRetriever, 
        DenseVectorRetriever, 
        SparseBM25Retriever,
        DocumentIngestionPipeline,
        DocumentChunk
    )
    RAG_AVAILABLE = True
    logger.info("Successfully imported RAG components from module-3-rag-systems")
except ImportError as e:
    logger.warning(f"RAG components not available: {e}")
    RAG_AVAILABLE = False
    HybridRetriever = None
    DenseVectorRetriever = None
    SparseBM25Retriever = None
    DocumentIngestionPipeline = None
    DocumentChunk = None

class MockRetriever:
    """Mock retriever for demo purposes when RAG is not available."""
    
    def __init__(self):
        self.name = "MockRetriever"
        logger.info("Initialized MockRetriever for demo")
    
    def search(self, query: str, top_k: int = 5):
        """Return mock results for demonstration."""
        logger.debug(f"MockRetriever searching for: '{query}' with top_k={top_k}")
        
        # Mock DocumentChunk-like objects
        class MockChunk:
            def __init__(self, chunk_id: str, text: str, section_number: int = 1):
                self.chunk_id = chunk_id
                self.text = text
                self.section_number = section_number
        
        # Mock policy results based on common expense policy questions
        mock_results = [
            (MockChunk("policy_1", "Daily per diem is $75 for meals and $150 for lodging when traveling for business."), 0.95),
            (MockChunk("policy_2", "All receipts must be submitted within 30 days of travel completion."), 0.87),
            (MockChunk("policy_3", "Alcohol expenses require prior manager approval and are limited to $25 per person."), 0.82),
            (MockChunk("policy_4", "Client entertainment expenses are limited to $100 per person and require business purpose documentation."), 0.78),
            (MockChunk("policy_5", "Travel advances must be reconciled within 2 weeks of return from travel."), 0.75),
            (MockChunk("policy_6", "Hotel expenses require itemized receipts and cannot exceed the per diem rate."), 0.72),
            (MockChunk("policy_7", "Airfare must be booked at least 14 days in advance to receive corporate rates."), 0.68),
            (MockChunk("policy_8", "Personal expenses mixed with business expenses will not be reimbursed."), 0.65),
        ]
        
        results = mock_results[:top_k]
        logger.info(f"MockRetriever returned {len(results)} results")
        return results


def create_hybrid_retriever(pdf_path: str = None, collection_name: str = "snapaudit_policies") -> Any:
    """
    Create and initialize a hybrid retriever using module-3-rag-systems components.
    
    Args:
        pdf_path: Path to the policy PDF file. If None, uses default sample policy.
        collection_name: Name for the Qdrant collection.
    
    Returns:
        HybridRetriever instance or MockRetriever if RAG components unavailable
    """
    if not RAG_AVAILABLE:
        logger.warning("RAG components not available, using MockRetriever")
        return MockRetriever()
    
    try:
        # Use default policy PDF if none provided
        if pdf_path is None:
            pdf_path = str(Path(__file__).resolve().parents[1] / "module-3-rag-systems" / "sample_expense_policy.pdf")
        
        logger.info(f"Creating hybrid retriever with PDF: {pdf_path}")
        
        # Initialize document ingestion pipeline
        pipeline = DocumentIngestionPipeline(pdf_path)
        chunks = pipeline.ingest()
        logger.info(f"Ingested {len(chunks)} document chunks")
        
        # Initialize dense retriever with Ollama embeddings
        dense = DenseVectorRetriever(collection_name=collection_name)
        dense.create_collection()
        dense.index_chunks(chunks)
        logger.info("Dense retriever initialized with Ollama embeddings")
        
        # Initialize sparse BM25 retriever
        sparse = SparseBM25Retriever()
        sparse.index_chunks(chunks)
        logger.info("Sparse BM25 retriever initialized")
        
        # Create hybrid retriever
        hybrid = HybridRetriever(
            dense_retriever=dense, 
            sparse_retriever=sparse,
            dense_weight=0.6,
            sparse_weight=0.4
        )
        logger.info("Hybrid retriever created successfully")
        
        return hybrid
        
    except Exception as e:
        logger.error(f"Failed to create hybrid retriever: {e}")
        logger.info("Falling back to MockRetriever")
        return MockRetriever()


def build_demo_crew(hybrid_retriever, ollama_base_url: str = None, ollama_model: str = None) -> Crew:
    logger.info("Building demo crew with retriever and generator")
    retriever_tool = RetrieverTool(hybrid_retriever)
    
    # Use provided parameters or fall back to environment variables
    base_url = ollama_base_url or OLLAMA_BASE_URL
    model = ollama_model or OLLAMA_MODEL
    
    generator = OllamaGenerator(base_url=base_url, model=model)
    logger.info(f"OllamaGenerator configured with URL: {base_url}, Model: {model}")

    retriever_agent = Agent(name="retriever", role="policy_retriever", tools={"retrieve": retriever_tool})
    summarizer_agent = Agent(name="summarizer", role="policy_summarizer", tools={"generate": generator})
    logger_agent = Agent(name="logger", role="audit_logger", tools={"log": logger_tool})

    crew = Crew([retriever_agent, summarizer_agent, logger_agent])
    logger.info("Demo crew built successfully")
    return crew

def demo_run(hybrid_retriever=None, question: str = "What is the daily per diem limit?", ollama_base_url: str = None, ollama_model: str = None):
    """
    Run a demo with the CrewAI system.
    
    Args:
        hybrid_retriever: Optional retriever instance. If None, creates one automatically.
        question: Question to process with the crew.
        ollama_base_url: Optional Ollama base URL. If None, uses environment variable.
        ollama_model: Optional Ollama model. If None, uses environment variable.
    
    Returns:
        Dictionary containing workflow results
    """
    logger.info(f"Starting demo run with question: {question}")
    
    # Use provided parameters or fall back to environment variables
    base_url = ollama_base_url or OLLAMA_BASE_URL
    model = ollama_model or OLLAMA_MODEL
    
    # Create retriever if not provided
    if hybrid_retriever is None:
        logger.info("No retriever provided, creating hybrid retriever automatically")
        hybrid_retriever = create_hybrid_retriever()
    
    # Build crew with the retriever and Ollama config
    crew = build_demo_crew(hybrid_retriever, base_url, model)
    
    # Define workflow
    workflow = [
        {"agent": "retriever", "action": "retrieve", "input": {"query": question, "top_k": 5}},
        {"agent": "summarizer", "action": "generate", "input": {"prompt": f"Summarize retrieved policy for: {question}"}},
        {"agent": "logger", "action": "log", "input": {"message": f"Question: {question}"}},
    ]
    
    # Run workflow
    outputs = crew.run_workflow(workflow)
    logger.info("Demo run completed successfully")
    return outputs


def quick_demo():
    """Quick demo function that can be called directly for testing."""
    logger.info("Running quick demo...")
    
    # Create retriever
    retriever = create_hybrid_retriever()
    
    # Run demo with sample question
    question = "What is the daily per diem limit for meals?"
    results = demo_run(retriever, question)
    
    logger.info("Quick demo completed")
    return results

if __name__ == "__main__":
    # Run a quick demo when executed directly
    try:
        logger.info("Running CrewAI demo from command line")
        results = quick_demo()
        
        print("\n" + "="*50)
        print("🤖 CrewAI Demo Results")
        print("="*50)
        
        for agent_name, agent_results in results.items():
            print(f"\n📋 {agent_name.upper()} RESULTS:")
            for i, result in enumerate(agent_results, 1):
                print(f"  {i}. {result}")
        
        print("\n✅ Demo completed successfully!")
        print("💡 To run the interactive Streamlit interface:")
        print("   uv run py -m streamlit run .\crew-ai\streamlit_app.py")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"❌ Demo failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Ensure Ollama is running: ollama serve")
        print("   2. Check environment variables are set")
        print("   3. Verify module-3-rag-systems is available")
