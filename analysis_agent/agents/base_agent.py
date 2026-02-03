"""Base Agent class with standardized logging and metrics tracking."""

import logging
import time
from typing import Optional, List
from datetime import datetime

from analysis_agent.core.models import AgentMetrics


class BaseAgent:
    """Base class for all agents with standardized logging and metrics."""
    
    def __init__(self, agent_name: str, settings: Optional['Settings'] = None):
        """
        Initialize base agent.
        
        Args:
            agent_name: Name of the agent (e.g., "PLANNING", "VISION", "OCR")
            settings: Application settings (optional)
        """
        self.agent_name = agent_name
        self.logger = self._setup_logger()
        self.llm_calls = 0
        self.total_time = 0.0
        
        # Initialize LLM Provider
        from analysis_agent.core.config import get_settings
        from analysis_agent.core.llm_provider import LLMFactory
        
        self.settings = settings or get_settings()
        self.llm = LLMFactory.create_provider(self.settings)

    def generate_llm_response(self, prompt: str, image_paths: Optional[List[str]] = None) -> str:
        """
        Generate text response from LLM using the configured provider.
        
        Args:
            prompt: Text prompt
            image_paths: Optional list of paths to images for vision tasks
            
        Returns:
            Generated text response
        """
        self.track_llm_call()
        try:
            return self.llm.generate(prompt, image_paths)
        except Exception as e:
            self.logger.error(f"LLM Generation failed: {e}")
            raise
    
    def _setup_logger(self) -> logging.Logger:
        """Setup standardized logger for this agent."""
        logger = logging.getLogger(f"{self.agent_name}")
        
        # Prevent duplicate logs - don't propagate to root logger
        logger.propagate = False
        
        # Only add handler if none exists
        if not logger.handlers:
            # Create custom formatter
            formatter = logging.Formatter(
                '%(asctime)s - VAA - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
    
    def track_llm_call(self):
        """Increment LLM call counter."""
        self.llm_calls += 1
    
    def create_metrics(self, phase: str, time_taken: float, llm_calls: int) -> AgentMetrics:
        """Create metrics object for this agent's work."""
        return AgentMetrics(
            agent_name=self.agent_name,
            time_taken=time_taken,
            llm_calls=llm_calls,
            phase=phase
        )
    
    def timed_operation(self, operation_name: str):
        """
        Context manager for timing operations.
        
        Usage:
            with self.timed_operation("Analysis"):
                # do work
        """
        return TimedOperation(self, operation_name)


class TimedOperation:
    """Context manager for timing agent operations."""
    
    def __init__(self, agent: BaseAgent, operation_name: str):
        self.agent = agent
        self.operation_name = operation_name
        self.start_time = None
        self.llm_calls_start = 0
    
    def __enter__(self):
        self.start_time = time.time()
        self.llm_calls_start = self.agent.llm_calls
        self.agent.logger.info(f"Starting {self.operation_name}...")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        llm_calls = self.agent.llm_calls - self.llm_calls_start
        
        if exc_type is None:
            self.agent.logger.info(
                f"Completed {self.operation_name} in {elapsed:.2f}s "
                f"({llm_calls} LLM calls)"
            )
        else:
            self.agent.logger.error(
                f"Failed {self.operation_name} after {elapsed:.2f}s: {exc_val}"
            )
        
        return False  # Don't suppress exceptions