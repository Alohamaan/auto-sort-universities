from admissions_agent.models import EmailThread


class GmailClient:
    """Stub interface for mailbox integration."""

    def fetch_new_threads(self) -> list[EmailThread]:
        return []
