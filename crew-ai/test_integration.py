#!/usr/bin/env python3
"""
Test script to demonstrate the CrewAI integration with module-3-rag-systems.

This script shows how to:
1. Import and use the actual hybrid retriever from module-3-rag-systems
2. Create a CrewAI crew with the retriever
3. Run a demo workflow
4. Handle fallback to mock retriever when RAG components are unavailable
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import CrewAI demo functions
from run_demo import create_hybrid_retriever, demo_run, quick_demo

def test_retriever_creation():
    """Test creating the hybrid retriever."""
    print("🔍 Testing hybrid retriever creation...")
    
    try:
        retriever = create_hybrid_retriever()
        
        if hasattr(retriever, 'name') and retriever.name == "MockRetriever":
            print("⚠️  Using MockRetriever (RAG components not available)")
        else:
            print("✅ Successfully created hybrid retriever with RAG components")
        
        # Test search functionality
        results = retriever.search("daily per diem", top_k=3)
        print(f"📊 Retrieved {len(results)} results:")
        for i, (text, score) in enumerate(results, 1):
            print(f"  {i}. [{score:.3f}] {text[:80]}...")
        
        return retriever
        
    except Exception as e:
        print(f"❌ Failed to create retriever: {e}")
        return None

def test_crew_workflow(retriever):
    """Test the CrewAI workflow."""
    print("\n🤖 Testing CrewAI workflow...")
    
    try:
        question = "What is the daily per diem limit for meals?"
        print(f"❓ Question: {question}")
        
        results = demo_run(hybrid_retriever=retriever, question=question)
        
        print("\n📋 Workflow Results:")
        for agent_name, agent_results in results.items():
            print(f"\n🔹 {agent_name.upper()}:")
            for i, result in enumerate(agent_results, 1):
                if isinstance(result, dict):
                    print(f"  {i}. {result}")
                elif isinstance(result, str):
                    print(f"  {i}. {result[:100]}...")
                else:
                    print(f"  {i}. {str(result)[:100]}...")
        
        return results
        
    except Exception as e:
        error_msg = str(e)
        if "Ollama" in error_msg or "connection" in error_msg.lower():
            print(f"⚠️  Ollama connection issue: {error_msg}")
            print("💡 Make sure Ollama is running with: ollama serve")
        else:
            print(f"❌ Workflow failed: {e}")
        return None

def test_quick_demo():
    """Test the quick demo function."""
    print("\n⚡ Testing quick demo...")
    
    try:
        results = quick_demo()
        print("✅ Quick demo completed successfully")
        return results
    except Exception as e:
        error_msg = str(e)
        if "Ollama" in error_msg or "connection" in error_msg.lower():
            print(f"⚠️  Ollama connection issue: {error_msg}")
            print("💡 Make sure Ollama is running with: ollama serve")
        else:
            print(f"❌ Quick demo failed: {e}")
        return None

def main():
    """Main test function."""
    print("🚀 CrewAI Integration Test")
    print("=" * 50)
    
    # Test 1: Retriever creation
    retriever = test_retriever_creation()
    
    # Test 2: Crew workflow (only if retriever was created)
    if retriever:
        test_crew_workflow(retriever)
    
    # Test 3: Quick demo
    test_quick_demo()
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")
    
    print("\n💡 Next steps:")
    print("1. Run the Streamlit interface: uv run py -m streamlit run .\crew-ai\streamlit_app.py")
    print("2. Try different questions about expense policies")
    print("3. Experiment with custom workflows")
    print("4. Check logs in the logs/ directory for detailed execution info")

if __name__ == "__main__":
    main()
