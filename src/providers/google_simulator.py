# src/providers/google_simulator.py
"""Simulates Google provider — Gemini-Pro, Gemini-Flash."""

import random
import time
from typing import Dict, List

from .base import BaseProvider, ProviderConfig, ProviderResponse

GOOGLE_MODELS = {
    "gemini-pro": {
        "latency_ms": 900,
        "cost_per_1k": 0.0005,
        "accuracy": 0.82,
        "tiers": ["free", "basic", "pro", "enterprise"],
    },
    "gemini-flash": {
        "latency_ms": 400,
        "cost_per_1k": 0.0001,
        "accuracy": 0.72,
        "tiers": ["free", "basic", "pro", "enterprise"],
    },
}

SIMULATED_RESPONSES = [
    "Here is a helpful and accurate response to your question.",
    "I can assist with that. Here are the key points.",
    "Let me provide you with a clear and concise answer.",
    "Based on my knowledge, here is what you need to know.",
    "Great question! Here is a direct and informative response.",
]


class GoogleSimulator(BaseProvider):

    def __init__(self, failure_rate: float = 0.04, latency_multiplier: float = 1.0):
        config = ProviderConfig(
            name="google",
            models=list(GOOGLE_MODELS.keys()),
            avg_latency_ms=650,
            cost_per_1k_tokens=0.0003,
            accuracy_score=0.77,
            failure_rate=failure_rate,
            latency_multiplier=latency_multiplier,
        )
        super().__init__(config)

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-flash",
    ) -> ProviderResponse:
        model_cfg = GOOGLE_MODELS.get(model, GOOGLE_MODELS["gemini-flash"])

        if random.random() < self.config.failure_rate:
            return ProviderResponse(
                model=model, provider="google", content="",
                prompt_tokens=0, completion_tokens=0,
                latency_ms=0, cost=0.0, success=False,
                error="503 Service Unavailable (simulated Google outage)",
            )

        base_ms = model_cfg["latency_ms"] * self.config.latency_multiplier
        latency_ms = int(base_ms * random.uniform(0.7, 1.3))
        time.sleep(latency_ms / 1000)

        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
        content = (
            f"[Google / {model}] {random.choice(SIMULATED_RESPONSES)} "
            f"(Re: '{user_msg[:60].strip()}...')"
        )

        prompt_tokens = max(10, sum(len(m["content"].split()) for m in messages) * 2)
        completion_tokens = max(10, len(content.split()) * 2)
        cost = self.estimate_cost(prompt_tokens, completion_tokens)

        return ProviderResponse(
            model=model, provider="google", content=content,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            latency_ms=latency_ms, cost=cost, success=True,
        )

    def health_check(self) -> bool:
        return random.random() > self.config.failure_rate
