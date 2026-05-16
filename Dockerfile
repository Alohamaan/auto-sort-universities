FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY admissions_agent ./admissions_agent
COPY tests ./tests
COPY docs ./docs
COPY .env.example ./.env.example

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .[dev]

EXPOSE 8000
CMD ["uvicorn", "admissions_agent.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
