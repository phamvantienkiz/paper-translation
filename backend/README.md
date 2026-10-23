# Paper Translation Backend

FastAPI backend for Paper Translation (Personal & Open-Source Edition).

## Setup & Running Locally

```bash
# 1. Create venv and install dependencies
uv venv .venv
uv pip install -e ".[dev]"

# 2. Run dev server
uv run uvicorn app.main:app --reload --port 8000
```
