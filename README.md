# llm-proxy

Remote language oracle for spreadsheet cells. Each cell serializes its neighborhood (values, formulas, TE weights, oscillator phase) and calls this server when local math produces an anomalous result. Returns LLM-generated insight via DeepInfra Seed-2.0-mini.

## Dependencies

none (standalone Python 3.10+)
Requires: `DEEPINFRA_KEY` environment variable

## Usage

```bash
export DEEPINFRA_KEY="your-key-here"
python3 llm_proxy.py
```

## API

### POST /oracle

```json
{
  "cell_id": 42,
  "tick": 137,
  "value": 0.723,
  "neighbors": [
    {"id": 7, "value": 0.91, "te_weight": 0.229},
    {"id": 13, "value": 0.34, "te_weight": 0.087}
  ],
  "prompt": "Why is my value 2.1σ above expected?"
}
```

Response:
```json
{
  "response": "Your value is elevated because Cell 7 (TE: 0.229) ...",
  "tokens_used": 142
}
```

### GET /health

Returns `{"status": "ok", "cells_served": 42}`

## Shell Loading

```python
from plato_shell_bridge import PlatoShell
shell = PlatoShell("agent-shell")
shell.load_tool("llm-proxy")
```

## Cost

~$0.50-5/day for anomaly-triggered LLM calls vs $100+/day for LLM-per-agent.

## License

MIT — Part of the Cocapn Fleet Intelligence System
