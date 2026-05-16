from datetime import UTC, datetime

from admissions_agent.jobs.poller import PollMailboxJob
from admissions_agent.models import EmailMessage, EmailThread


class FakeGmail:
    def __init__(self) -> None:
        self.add_label_calls: list[tuple[str, str]] = []

    def rules_from_dict(self, rules: dict):
        return rules

    def update_rules(self, rules) -> None:
        return None

    def search_candidate_threads(self, query: str) -> list[str]:
        return ["thread-1"]

    def fetch_thread(self, thread_id: str) -> EmailThread:
        return EmailThread(
            thread_id=thread_id,
            snippet="Admissions inquiry",
            messages=[
                EmailMessage(
                    message_id="m1",
                    from_address="admissions@uni.edu",
                    subject="Admissions",
                    body_text="Question about admission",
                    sent_at=datetime(2026, 5, 2, tzinfo=UTC),
                )
            ],
        )

    def add_label(self, thread_id: str, label_name: str) -> None:
        self.add_label_calls.append((thread_id, label_name))

    def get_history_since(self, history_id: str):
        return {}


class FakeSheets:
    def __init__(self) -> None:
        self.review_queue_calls = 0
        self.agent_log_calls = 0

    def load_applications(self):
        return []

    def load_email_rules(self):
        return {}

    def append_review_queue(self, payload):
        self.review_queue_calls += 1

    def append_agent_log(self, payload):
        self.agent_log_calls += 1

    def apply_patch_to_application(self, patch):
        return {}


def test_dry_run_prints_actions_without_writes() -> None:
    logs: list[str] = []
    gmail = FakeGmail()
    sheets = FakeSheets()

    job = PollMailboxJob(gmail=gmail, sheets=sheets, dry_run=True, print_fn=logs.append)
    decisions = job.run_once()

    assert decisions
    assert sheets.review_queue_calls == 0
    assert sheets.agent_log_calls == 0
    assert gmail.add_label_calls == []
    assert any(line.startswith("DRY-RUN:") for line in logs)
