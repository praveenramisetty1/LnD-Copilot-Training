# Evaluation Mapping

| Judge Criterion | What We Will Build | Artifact | Demo Evidence |
|---|---|---|---|
| NFR Parsing | Parse latency, cost, accuracy headers | Routing Engine | Request with headers |
| Model Selection | Score providers by latency/cost/accuracy | Router Service | Routing decision output |
| Failover Strategy | Simulate provider outage and fallback | Failover Engine | Provider A fails, Provider B used |
| Semantic Caching | Cache semantically similar prompts | Cache Manager | First call miss, second call hit |
| Cost Tracking | Track estimated provider cost | Analytics Collector | Dashboard metrics |
| Security | No hardcoded API keys, config-based secrets | Security Architecture | Config and README |
| Performance | P95 routing latency target documented/tested | Performance Tests | Test result or skeleton |
| Business Value | Show reduced API calls through cache | ROI Document | Cost comparison |
``