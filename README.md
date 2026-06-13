# LLM Proxy

A **rate-limited HTTP proxy** that intercepts spreadsheet cell update requests, constructs context-aware prompts, forwards them to DeepInfra's Seed-2.0-mini LLM, and returns oracle values — enabling cellular automata to use a language model as their transition function.

## Why It Matters

Traditional cellular automata use fixed rules (Conway's Life, Wolfram's Rule 30). This proxy enables a new paradigm: each cell queries an LLM for its next value based on its current state and neighborhood. The LLM acts as an oracle — a context-aware transition function that can produce emergent, creative patterns impossible with fixed rules. The proxy handles the engineering challenges: rate limiting (LLMs are expensive and slow), prompt construction (encoding cell state + neighbors as text), response parsing (extracting a float from free-form LLM output), and error handling (timeouts, parse failures, API errors). Without this proxy, every cell would need its own API client, duplicating rate-limiting and parsing logic.

## How It Works

**Architecture**:
```
Spreadsheet Engine
    ↓  POST /oracle {cell_id, tick, value, neighbors, phase}
LLM Proxy (this)
    ↓  Construct prompt
    ↓  Rate limit check (sliding window)
    ↓  POST to DeepInfra API
DeepInfra Seed-2.0-mini
    ↓  Returns chat completion
LLM Proxy
    ↓  Parse response → extract float
    ↓  Return {cell_id, tick, oracle_value}
Spreadsheet Engine
```

**Prompt construction**: The proxy converts cell state into a natural language prompt:
```
"You are a cell in a spreadsheet simulation.
Cell 42 has value 0.3142.
Neighbors: [{value: 0.1}, {value: -0.5}, {value: 0.8}].
Phase: 0.5.
Suggest a next value (float, range -1.0 to 1.0) that
continues an interesting pattern.
Respond with ONLY a JSON object: {\"value\": <float>}"
```

**Rate limiting**: A sliding-window rate limiter using a `deque` of timestamps. Each request checks if `len(timestamps) < RATE_LIMIT` within the `RATE_WINDOW`. If exceeded, returns HTTP 429. This prevents runaway API costs.

```python
def check_rate_limit():
    now = time.time()
    while timestamps and now - timestamps[0] > WINDOW:
        timestamps.popleft()
    if len(timestamps) >= LIMIT:
        return False  # rate limited
    timestamps.append(now)
    return True
```

**Response parsing**: LLMs return free-form text, not structured data. The parser tries (in order):
1. Parse as JSON, extract `value` field
2. Find first JSON object in response text, parse
3. Regex extract first float, clamp to [-1.0, 1.0]
4. Return None (parse failure → HTTP 500)

**Configuration**:
- Model: `ByteDance/Seed-2.0-mini`
- Max tokens: 50 (keep responses short)
- Temperature: 0.85 (encourage variety in suggested values)
- Rate limit: 10 requests/second
- Timeout: 10 seconds per API call

**Complexity**: O(1) per request (excluding API call latency, which is O(LLM inference time) — typically 200-2000ms).

## Quick Start

```bash
# Set your DeepInfra API key
export DEEPINFRA_API_KEY="your-key-here"

# Or store in credentials vault
echo '{"DEEPINFRA_API_KEY": "your-key"}' > ~/.credentials_vault

# Start the proxy
python llm_proxy.py

# Test
curl http://localhost:8866/health
curl -X POST http://localhost:8866/oracle \
  -H "Content-Type: application/json" \
  -d '{"cell_id": 1, "tick": 0, "value": 0.5, "neighbors": [{"value": 0.3}], "phase": 0.1}'
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health + current rate |
| `/oracle` | POST | Cell oracle query (returns suggested next value) |

**POST /oracle body**:
```json
{"cell_id": 1, "tick": 0, "value": 0.5, "neighbors": [...], "phase": 0.1}
```

**Response**:
```json
{"cell_id": 1, "tick": 0, "oracle_value": 0.73, "model": "Seed-2.0-mini", "latency_ms": 842}
```

## Architecture Notes

LLM Proxy bridges the SuperInstance cellular automaton and external AI inference. It's a **γ**-reduction mechanism in **γ + η = C**: rate limiting prevents API cost explosion (bounded γ), while the LLM oracle provides creative emergence (high η). The proxy is stateless — all cell context is passed per-request. See [Architecture](https://github.com/SuperInstance/SuperInstance/blob/main/ARCHITECTURE.md).

## References

- Wolfram, S. *A New Kind of Science*, Wolfram Media (2002). — Cellular automata as computation.
- DeepInfra API Documentation. https://deepinfra.com/docs
- von Neumann, J. *Theory of Self-Reproducing Automata*, UIUC Press (1966).

## License

MIT
