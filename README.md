# Admissions Email Reconciliation Agent (Skeleton)

Initial Python 3.12 skeleton for an agent that processes admissions-related email threads and proposes controlled tracker updates.

## Guardrails
- The LLM/classifier layer **never writes directly** to Google Sheets.
- Classifier output is structured only.
- `DecisionEngine` applies deterministic rules and returns one of:
  - ignore
  - review queue item
  - pending action requiring human approval (e.g., via Telegram)

## Project Structure
- `admissions_agent/app.py` - FastAPI webhook surface
- `admissions_agent/models.py` - Pydantic v2 schemas
- `admissions_agent/enums.py` - status and decision enums
- `admissions_agent/decision_engine.py` - deterministic policy checks
- `admissions_agent/telegram.py` - Telegram message renderer
- `admissions_agent/gmail.py` - Gmail interface stub
- `admissions_agent/sheets.py` - Google Sheets interface stub (dry-run)
- `admissions_agent/resolver.py` - institution resolver stub
- `admissions_agent/classifier.py` - classifier stub
- `admissions_agent/jobs.py` - polling orchestration
- `admissions_agent/db.py` - SQLite table bootstrap

## Local setup
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

## Run app

Entrypoint module used in Docker/production is `admissions_agent.app:app`.

```bash
uvicorn admissions_agent.app:app --reload
```

## Run tests
```bash
pytest
```

## Docker (local dev)
```bash
docker compose up --build
```

## Production CI/CD

### Server bootstrap checklist
1. Install Docker Engine + Compose plugin on the VPS.
2. Create deployment directory (e.g. `/opt/admissions-agent`) and copy:
   - `docker-compose.prod.yml`
   - `.env` (from `.env.example`, with real values)
3. Ensure `/opt/admissions-agent/data` exists and is writable.
4. Ensure GHCR pull access is configured on the server (`docker login ghcr.io`).

### GitHub secrets (for deploy workflow)
- `PROD_SSH_HOST`
- `PROD_SSH_USER`
- `PROD_SSH_PRIVATE_KEY`
- `PROD_SSH_PORT`
- `PROD_APP_DIR`

> Do not store application runtime secrets in GitHub Actions secrets. Keep runtime values in the server `.env` file.

### First deploy steps
1. Merge to `main` (triggers CI and deploy workflows).
2. Verify image is pushed to GHCR:
   - `ghcr.io/<owner>/admissions-agent:latest`
   - `ghcr.io/<owner>/admissions-agent:<git_sha>`
3. Confirm service state on VPS:
   - `docker compose -f docker-compose.prod.yml ps`

### Rollback command
```bash
APP_IMAGE_TAG=<previous_git_sha> docker compose -f docker-compose.prod.yml up -d --remove-orphans
```

### Inspect logs
```bash
docker compose -f docker-compose.prod.yml logs -f app
```

## Notes
- No production Gmail/Sheets/OpenAI calls are implemented.
- Tests use local fixtures and do not send emails or write to real spreadsheets.
