from typing import Any, Dict, List, Callable, Optional
import time
import sys
from pathlib import Path

# Import centralized logging configuration
sys.path.append(str(Path(__file__).resolve().parents[1]))
from logger_config import get_logger

# Initialize logger for this module
logger = get_logger(__name__)

class Agent:
    """
    Minimal Agent abstraction.
    - role: human-readable role name (e.g., 'retriever', 'summarizer')
    - tools: dict of callables the agent can use
    - memory: simple list of messages (append-only)
    """

    def __init__(self, name: str, role: str, tools: Optional[Dict[str, Callable]] = None):
        logger.info(f"Initializing Agent: {name} with role: {role}")
        self.name = name
        self.role = role
        self.tools = tools or {}
        self.memory: List[Dict[str, Any]] = []
        logger.debug(f"Agent {name} initialized with {len(self.tools)} tools")

    def remember(self, item: Dict[str, Any]) -> None:
        """Append to agent memory."""
        logger.debug(f"Agent {self.name} remembering item: {item.get('type', 'unknown')}")
        self.memory.append({"ts": time.time(), **item})

    def call_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """Invoke a named tool; raise if missing."""
        if tool_name not in self.tools:
            logger.error(f"Tool '{tool_name}' not available to agent '{self.name}'")
            raise ValueError(f"Tool '{tool_name}' not available to agent '{self.name}'")
        logger.debug(f"Agent {self.name} calling tool {tool_name}")
        return self.tools[tool_name](*args, **kwargs)

    def act(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Default action: store prompt in memory and return a simple plan.
        Override in specialized agents or provide custom tools.
        """
        logger.debug(f"Agent {self.name} acting on prompt: {prompt[:50]}...")
        self.remember({"type": "prompt", "prompt": prompt, "context": context})
        result = {"agent": self.name, "role": self.role, "plan": f"Received prompt: {prompt[:120]}"}
        logger.info(f"Agent {self.name} completed action: {result['plan'][:50]}...")
        return result
