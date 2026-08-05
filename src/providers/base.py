# src/providers/base.py
"""Abstract base class for all LLM provider simulators."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Message:
    role: str    # system | user | assistant
    content: str


@dataclass
class ProviderResponse:
    model: str
    provider: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    cost: float
    success: bool
    error: Optional[str] = None


@dataclass
class ProviderConfig:
    name: str
    models: List[str]
    avg_latency_ms: int
    cost_per_1k_tokens: float
    accuracy_score: float        # 0.0 – 1.0
    failure_rate: float          # 0.0 = never fails, 1.0 = always fails
    latency_multiplier: float = 1.0


class BaseProvider(ABC):
    """All provider simulators inherit from this class."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
    ) -> ProviderResponse:
        """Execute a chat completion and return a ProviderResponse."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is considered healthy."""

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        total = prompt_tokens + completion_tokens
        return round((total / 1000) * self.config.cost_per_1k_tokens, 6)
