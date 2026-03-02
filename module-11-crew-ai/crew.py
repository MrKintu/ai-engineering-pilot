from typing import List, Dict, Any
import sys
from pathlib import Path

# Import centralized logging configuration
sys.path.append(str(Path(__file__).resolve().parents[1]))
from logger_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

from agents import Agent

class Crew:
    """
    Orchestrates a small team of agents.
    - agents: list of Agent instances
    - workflow: ordered list of (agent_name, task_spec) tuples
    """

    def __init__(self, agents: List[Agent]):
        logger.info(f"Initializing Crew with {len(agents)} agents")
        self.agents_by_name = {a.name: a for a in agents}
        logger.debug(f"Crew agents: {list(self.agents_by_name.keys())}")

    def run_workflow(self, workflow: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        workflow: list of dicts:
          {"agent": "retriever", "action": "retrieve", "input": {"query": "...", "top_k": 5}}
        Returns aggregated outputs.
        """
        logger.info(f"Starting workflow with {len(workflow)} steps")
        outputs = {}
        for i, step in enumerate(workflow):
            agent_name = step["agent"]
            action = step.get("action")
            inp = step.get("input", {})
            agent = self.agents_by_name.get(agent_name)
            if not agent:
                logger.error(f"Agent '{agent_name}' not found in crew")
                raise ValueError(f"Agent '{agent_name}' not found in crew")
            logger.info(f"Running step {i+1}: agent={agent_name} action={action}")
            # Simple dispatch: if action maps to a tool name, call it
            if action in agent.tools:
                result = agent.call_tool(action, **inp)
            else:
                # fallback: agent.act
                result = agent.act(inp.get("prompt", ""), context=inp)
            outputs.setdefault(agent_name, []).append(result)
            logger.debug(f"Step {i+1} completed successfully")
        logger.info("Workflow completed successfully")
        return outputs
