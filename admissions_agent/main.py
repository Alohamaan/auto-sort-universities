from fastapi import FastAPI

from admissions_agent.jobs import PollMailboxJob

app = FastAPI(title="Admissions Email Reconciliation Agent")
job = PollMailboxJob()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/gmail")
def gmail_webhook() -> dict:
    return {"processed": job.run_once()}


@app.post("/webhooks/telegram")
def telegram_webhook() -> dict[str, str]:
    return {"status": "received"}
