# Admissions Email Reconciliation Agent (Skeleton)

Python 3.12 agent that processes admissions-related email threads and proposes controlled tracker updates.

## Guardrails
- The LLM/classifier layer **never writes directly** to Google Sheets.
- Classifier output is structured only.
- `DecisionEngine` applies deterministic rules and returns one of:
  - ignore
  - review queue item
  - pending action requiring human approval (e.g., via Telegram)

## Project Structure
- `admissions_agent/main.py` - FastAPI webhook surface
- `admissions_agent/models.py` - Pydantic v2 schemas
- `admissions_agent/enums.py` - status and decision enums
- `admissions_agent/decision_engine.py` - deterministic policy checks
- `admissions_agent/telegram.py` - Telegram message renderer
- `admissions_agent/gmail.py` - Gmail interface stub
- `admissions_agent/sheets.py` - Google Sheets interface stub (dry-run)
- `admissions_agent/resolver.py` - institution resolver stub
- `admissions_agent/classifier.py` - classifier stub
- `admissions_agent/jobs/` - polling orchestration and reconcile CLI
- `admissions_agent/db.py` - SQLite table bootstrap

## Local setup
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

## Run app
```bash
uvicorn admissions_agent.main:app --reload
```

## Reconcile mailbox (one-shot)
```bash
python -m admissions_agent.jobs.reconcile --dry-run
```

Dry-run prints proposed actions and does not write to Gmail or Google Sheets.

## Run tests
```bash
pytest
```

## Docker
```bash
docker compose up --build
```

## Notes
- Gmail and Google Sheets integrations are behind interfaces and can be replaced with fakes in tests.
- Tests use local fixtures and do not send emails or write to real spreadsheets.
