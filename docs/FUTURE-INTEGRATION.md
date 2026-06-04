# Future Integration: llm-proxy

## Current State
A remote language oracle for spreadsheet cells. Each cell serializes its neighborhood (values, formulas, TE weights, oscillator phase) and calls the server when local math produces anomalous results. Returns LLM-generated insight via DeepInfra Seed-2.0-mini. Standalone Python, requires `DEEPINFRA_KEY`.

## Integration Opportunities

### With PLATO
The llm-proxy becomes PLATO's API key management layer. Currently, every Codespace and every agent would need its own API keys. The proxy centralizes key management: agents call the proxy, the proxy calls the LLM provider, keys never leave the proxy. This is exactly what the room-as-codespace architecture needs — ensigns in Codespaces call back through PLATO for LLM reasoning.

### With ternary-cell
When a ternary cell's `surprise` phase produces an anomaly (prediction far from perception), the cell's local logic may not explain why. The llm-proxy provides the escalation path: serialize cell state, send to proxy, receive natural language insight. This is the cell's "ask for help" mechanism.

### With construct-core
At Layer 2 (AsyncConstruct), agents can make network calls. The llm-proxy becomes a standard tool: `request_tool("llm-proxy")` returns a handle for LLM queries. The proxy manages rate limiting, key rotation, and model selection transparently.

## Dormant Ideas Now Unlockable
The proxy was designed for a single user's spreadsheet. With the fleet architecture, it becomes a shared service: multiple rooms, multiple agents, multiple models — all routing through one proxy that manages keys, budgets, and priorities. The `POST /oracle` endpoint extends to handle fleet-wide LLM requests with priority queuing.

## Potential in Mature Systems
The llm-proxy evolves into PLATO's central intelligence gateway. Every LLM call in the fleet goes through it. It manages model selection (fast model for routine queries, powerful model for complex reasoning), tracks usage per room and per agent, enforces budget limits, and provides audit logs. Combined with fastloop-guard, it caches repeated queries for instant response.

## Cross-Pollination Ideas
- **fastloop-guard**: Three-gate cache sits in front of the proxy for instant cache hits
- **captains-log**: Proxy usage logs feed into fleet history
- **oracle1-vessel**: Oracle1 runs the proxy on Oracle Cloud as a fleet service

## Dependencies for Next Steps
- Multi-tenant request routing (room ID, agent ID)
- Model selection strategy (cost vs quality)
- Integration with construct-core's tool request API
