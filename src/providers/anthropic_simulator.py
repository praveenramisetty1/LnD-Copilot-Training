# src/providers/anthropic_simulator.py
"""Simulates Anthropic provider — Claude-3-Opus, Claude-3-Sonnet, Claude-3-Haiku."""

import time
import random
from typing import List, Dict

from .base import BaseProvider, ProviderConfig, ProviderResponse


ANTHROPIC_MODELS = {
    "claude-3-opus": {
        "latency_ms": 1800,
        "cost_per_1k": 0.015,
        "accuracy": 0.94,
        "tiers": ["pro", "enterprise"],
    },
    "claude-3-sonnet": {
        "latency_ms": 1200,
        "cost_per_1k": 0.003,
        "accuracy": 0.88,
        "tiers": ["basic", "pro", "enterprise"],
    },
    "claude-3-haiku": {
        "latency_ms": 600,
        "cost_per_1k": 0.0002,
        "accuracy": 0.78,
        "tiers": ["free", "basic", "pro", "enterprise"],
    },
}

SIMULATED_RESPONSES = [
    "I'd be happy to help with that. Here's my analysis.",
    "That's an interesting question. Let me provide a thorough response.",
    "Based on careful consideration, here is what I think.",
    "I'll approach this systematically to give you the best answer.",
    "Here is a well-reasoned response to your query.",
]


class AnthropicSimulator(BaseProvider):

    def __init__(self, failure_rate: float = 0.03, latency_multiplier: float = 1.0):
        config = ProviderConfig(
            name="anthropic",
            models=list(ANTHROPIC_MODELS.keys()),
            avg_latency_ms=1200,
            cost_per_1k_tokens=0.006,
            accuracy_score=0.87,
            failure_rate=failure_rate,
            latency_multiplier=latency_multiplier,
        )
        super().__init__(config)

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-haiku",
    ) -> ProviderResponse:
        model_cfg = ANTHROPIC_MODELS.get(model, ANTHROPIC_MODELS["claude-3-haiku"])

        if random.random() < self.config.failure_rate:
            return ProviderResponse(
                model=model, provider="anthropic", content="",
                prompt_tokens=0, completion_tokens=0,
                latency_ms=0, cost=0.0, success=False,
                error="503 Service Unavailable (simulated Anthropic outage)",
            )

        base_ms = model_cfg["latency_ms"] * self.config.latency_multiplier
        latency_ms = int(base_ms * random.uniform(0.7, 1.3))
        time.sleep(latency_ms / 1000)

        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        content = (
            f"[Anthropic / {model}] {random.choice(SIMULATED_RESPONSES)} "
            f"(Re: '{user_msg[:60].strip()}...')"
        )

        prompt_tokens = max(10, sum(len(m["content"].split()) for m in messages) * 2)
        completion_tokens = max(10, len(content.split()) * 2)
        cost = self.estimate_cost(prompt_tokens, completion_tokens)

        return ProviderResponse(
            model=model, provider="anthropic", content=content,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            latency_ms=latency_ms, cost=cost, success=True,
        )

    def health_check(self) -> bool:
        return random.random() > self.config.failure_rate
