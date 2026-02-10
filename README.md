## PoC: pydantic + pydantic-ai

Install dependencies:

```bash
uv sync
```

Run the PoC in deterministic fallback mode (no API key needed):

```bash
uv run python examples/pydanticai_poc.py
```

Run with a real model path (guarded by env vars):

```bash
export OPENAI_API_KEY="your_key"
export POKECOACH_PYDANTICAI_MODEL="openai:gpt-4o-mini"
uv run python examples/pydanticai_poc.py
```
