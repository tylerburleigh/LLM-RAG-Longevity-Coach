# coach/callbacks.py
"""LangChain callbacks for observability and monitoring."""

import logging
import time
from typing import Dict, List, Any, Optional, Union
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document

from coach.config import config

logger = logging.getLogger(__name__)


class LoggingCallbackHandler(BaseCallbackHandler):
    """Callback handler for detailed logging of LangChain operations."""
    
    def __init__(self, log_level: str = "INFO"):
        super().__init__()
        self.log_level = getattr(logging, log_level.upper())
        self.logger = logging.getLogger(f"{__name__}.LoggingCallback")
        self.logger.setLevel(self.log_level)
        
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts running."""
        self.logger.info(f"LLM started with {len(prompts)} prompts")
        if self.log_level <= logging.DEBUG:
            self.logger.debug(f"Prompts: {prompts}")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Called when LLM ends running."""
        self.logger.info(f"LLM completed with {len(response.generations)} generations")
        if self.log_level <= logging.DEBUG:
            self.logger.debug(f"Response: {response}")
    
    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Called when LLM errors."""
        self.logger.error(f"LLM error: {error}")
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Called when chain starts running."""
        chain_name = serialized.get("name", "Unknown")
        self.logger.info(f"Chain '{chain_name}' started")
        if self.log_level <= logging.DEBUG:
            self.logger.debug(f"Inputs: {inputs}")
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Called when chain ends running."""
        self.logger.info("Chain completed")
        if self.log_level <= logging.DEBUG:
            self.logger.debug(f"Outputs: {outputs}")
    
    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Called when chain errors."""
        self.logger.error(f"Chain error: {error}")
    
    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        **kwargs: Any,
    ) -> None:
        """Called when retriever starts running."""
        self.logger.info(f"Retriever started with query: {query}")
    
    def on_retriever_end(self, documents: List[Document], **kwargs: Any) -> None:
        """Called when retriever ends running."""
        self.logger.info(f"Retriever completed with {len(documents)} documents")
        if self.log_level <= logging.DEBUG:
            for i, doc in enumerate(documents):
                self.logger.debug(f"Document {i}: {doc.page_content[:100]}...")
    
    def on_retriever_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Called when retriever errors."""
        self.logger.error(f"Retriever error: {error}")


class PerformanceCallbackHandler(BaseCallbackHandler):
    """Callback handler for performance monitoring."""
    
    def __init__(self):
        super().__init__()
        self.start_times: Dict[str, float] = {}
        self.performance_metrics: Dict[str, List[float]] = {}
        self.logger = logging.getLogger(f"{__name__}.PerformanceCallback")
    
    def _get_run_id(self, kwargs: Dict[str, Any]) -> str:
        """Get a unique run ID for tracking."""
        return str(kwargs.get("run_id", "unknown"))
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Track LLM start time."""
        run_id = self._get_run_id(kwargs)
        self.start_times[f"llm_{run_id}"] = time.time()
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Track LLM end time and calculate duration."""
        run_id = self._get_run_id(kwargs)
        start_time = self.start_times.pop(f"llm_{run_id}", None)
        
        if start_time:
            duration = time.time() - start_time
            if "llm_duration" not in self.performance_metrics:
                self.performance_metrics["llm_duration"] = []
            self.performance_metrics["llm_duration"].append(duration)
            
            # Log token usage if available
            if hasattr(response, 'llm_output') and response.llm_output:
                token_usage = response.llm_output.get('token_usage', {})
                if token_usage:
                    self.logger.info(f"LLM completed in {duration:.2f}s, tokens: {token_usage}")
                else:
                    self.logger.info(f"LLM completed in {duration:.2f}s")
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Track chain start time."""
        run_id = self._get_run_id(kwargs)
        self.start_times[f"chain_{run_id}"] = time.time()
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Track chain end time and calculate duration."""
        run_id = self._get_run_id(kwargs)
        start_time = self.start_times.pop(f"chain_{run_id}", None)
        
        if start_time:
            duration = time.time() - start_time
            if "chain_duration" not in self.performance_metrics:
                self.performance_metrics["chain_duration"] = []
            self.performance_metrics["chain_duration"].append(duration)
            self.logger.info(f"Chain completed in {duration:.2f}s")
    
    def on_retriever_start(
        self,
        serialized: Dict[str, Any],
        query: str,
        **kwargs: Any,
    ) -> None:
        """Track retriever start time."""
        run_id = self._get_run_id(kwargs)
        self.start_times[f"retriever_{run_id}"] = time.time()
    
    def on_retriever_end(self, documents: List[Document], **kwargs: Any) -> None:
        """Track retriever end time and calculate duration."""
        run_id = self._get_run_id(kwargs)
        start_time = self.start_times.pop(f"retriever_{run_id}", None)
        
        if start_time:
            duration = time.time() - start_time
            if "retriever_duration" not in self.performance_metrics:
                self.performance_metrics["retriever_duration"] = []
            self.performance_metrics["retriever_duration"].append(duration)
            self.logger.info(f"Retriever completed in {duration:.2f}s, found {len(documents)} documents")
    
    def get_performance_summary(self) -> Dict[str, Dict[str, float]]:
        """Get a summary of performance metrics."""
        summary = {}
        
        for metric_name, durations in self.performance_metrics.items():
            if durations:
                summary[metric_name] = {
                    "count": len(durations),
                    "total": sum(durations),
                    "average": sum(durations) / len(durations),
                    "min": min(durations),
                    "max": max(durations),
                }
        
        return summary
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.performance_metrics.clear()
        self.start_times.clear()


class CostTrackingCallbackHandler(BaseCallbackHandler):
    """Callback handler for tracking API costs."""
    
    def __init__(self):
        super().__init__()
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        self.api_calls = 0
        self.logger = logging.getLogger(f"{__name__}.CostTrackingCallback")
    
    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Track token usage and costs."""
        self.api_calls += 1
        
        if hasattr(response, 'llm_output') and response.llm_output:
            token_usage = response.llm_output.get('token_usage', {})
            if token_usage:
                self.token_usage["prompt_tokens"] += token_usage.get("prompt_tokens", 0)
                self.token_usage["completion_tokens"] += token_usage.get("completion_tokens", 0)
                self.token_usage["total_tokens"] += token_usage.get("total_tokens", 0)
                
                self.logger.info(f"API call #{self.api_calls}, tokens: {token_usage}")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get a summary of costs (basic estimation)."""
        # These are rough estimates - actual costs depend on the model and provider
        estimated_cost_per_1k_tokens = 0.002  # Rough estimate
        
        estimated_cost = (self.token_usage["total_tokens"] / 1000) * estimated_cost_per_1k_tokens
        
        return {
            "api_calls": self.api_calls,
            "token_usage": self.token_usage,
            "estimated_cost_usd": estimated_cost,
            "note": "Cost estimates are approximate and may vary by provider and model"
        }
    
    def reset_tracking(self):
        """Reset all cost tracking."""
        self.token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        self.api_calls = 0


class CallbackManager:
    """Manager for LangChain callbacks."""
    
    def __init__(self):
        self.callbacks = {}
        self.logger = logging.getLogger(f"{__name__}.CallbackManager")
    
    def add_callback(self, name: str, callback: BaseCallbackHandler):
        """Add a callback handler."""
        self.callbacks[name] = callback
        self.logger.info(f"Added callback: {name}")
    
    def remove_callback(self, name: str):
        """Remove a callback handler."""
        if name in self.callbacks:
            del self.callbacks[name]
            self.logger.info(f"Removed callback: {name}")
    
    def get_callbacks(self) -> List[BaseCallbackHandler]:
        """Get all callback handlers as a list."""
        return list(self.callbacks.values())
    
    def get_callback(self, name: str) -> Optional[BaseCallbackHandler]:
        """Get a specific callback handler."""
        return self.callbacks.get(name)
    
    def clear_callbacks(self):
        """Clear all callback handlers."""
        self.callbacks.clear()
        self.logger.info("Cleared all callbacks")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary from all performance callbacks."""
        summary = {}
        
        for name, callback in self.callbacks.items():
            if isinstance(callback, PerformanceCallbackHandler):
                summary[name] = callback.get_performance_summary()
        
        return summary
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary from all cost tracking callbacks."""
        summary = {}
        
        for name, callback in self.callbacks.items():
            if isinstance(callback, CostTrackingCallbackHandler):
                summary[name] = callback.get_cost_summary()
        
        return summary


def create_default_callbacks(
    enable_logging: bool = True,
    enable_performance: bool = True,
    enable_cost_tracking: bool = True,
    log_level: str = "INFO"
) -> CallbackManager:
    """
    Create a callback manager with default callbacks.
    
    Args:
        enable_logging: Whether to enable logging callbacks
        enable_performance: Whether to enable performance monitoring
        enable_cost_tracking: Whether to enable cost tracking
        log_level: Log level for the logging callback
        
    Returns:
        CallbackManager with configured callbacks
    """
    manager = CallbackManager()
    
    if enable_logging:
        manager.add_callback("logging", LoggingCallbackHandler(log_level))
    
    if enable_performance:
        manager.add_callback("performance", PerformanceCallbackHandler())
    
    if enable_cost_tracking:
        manager.add_callback("cost_tracking", CostTrackingCallbackHandler())
    
    return manager


# Global callback manager instance
callback_manager = create_default_callbacks(
    log_level=config.LOG_LEVEL
)