# src/providers/openai_simulator.py
"""Simulates OpenAI provider — GPT-4, GPT-4-Turbo, GPT-3.5-Turbo."""

import random
import time
from typing import Dict, List

from .base import BaseProvider, ProviderConfig, ProviderResponse

OPENAI_MODELS = {
    "gpt-4": {
        "latency_ms": 2000,
        "cost_per_1k": 0.030,
        "accuracy": 0.95,
        "tiers": ["pro", "enterprise"],
    },
    "gpt-4-turbo": {
        "latency_ms": 1500,
        "cost_per_1k": 0.010,
        "accuracy": 0.93,
        "tiers": ["basic", "pro", "enterprise"],
    },
    "gpt-3.5-turbo": {
        "latency_ms": 800,
        "cost_per_1k": 0.001,
        "accuracy": 0.80,
        "tiers": ["free", "basic", "pro", "enterprise"],
    },
}

SIMULATED_RESPONSES = [
    "This is a thoughtful and well-structured answer to your question.",
    "Based on the context provided, here is a detailed explanation.",
    "Great question! The answer involves several key considerations.",
    "Let me break this down step by step for clarity.",
    "Here is a comprehensive response covering the main points.",
]


class OpenAISimulator(BaseProvider):

    def __init__(self, failure_rate: float = 0.05, latency_multiplier: float = 1.0):
        config = ProviderConfig(
            name="openai",
            models=list(OPENAI_MODELS.keys()),
            avg_latency_ms=1433,
            cost_per_1k_tokens=0.014,
            accuracy_score=0.89,
            failure_rate=failure_rate,
            latency_multiplier=latency_multiplier,
        )
        super().__init__(config)

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
    ) -> ProviderResponse:
        model_cfg = OPENAI_MODELS.get(model, OPENAI_MODELS["gpt-3.5-turbo"])

        # Simulate random failure
        if random.random() < self.config.failure_rate:
            return ProviderResponse(
                model=model, provider="openai", content="",
                prompt_tokens=0, completion_tokens=0,
                latency_ms=0, cost=0.0, success=False,
                error="503 Service Unavailable (simulated OpenAI outage)",
            )

        # Simulate realistic latency
        base_ms = model_cfg["latency_ms"] * self.config.latency_multiplier
        latency_ms = int(base_ms * random.uniform(0.7, 1.3))
        time.sleep(latency_ms / 1000)

        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        content = (
            f"[OpenAI / {model}] {random.choice(SIMULATED_RESPONSES)} "
            f"(Re: '{user_msg[:60].strip()}...')"
        )

        prompt_tokens = max(10, sum(len(m["content"].split()) for m in messages) * 2)
        completion_tokens = max(10, len(content.split()) * 2)
        cost = self.estimate_cost(prompt_tokens, completion_tokens)

        return ProviderResponse(
            model=model, provider="openai", content=content,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            latency_ms=latency_ms, cost=cost, success=True,
        )

    def health_check(self) -> bool:
        return random.random() > self.config.failure_rate
