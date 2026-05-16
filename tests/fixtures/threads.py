from datetime import datetime, UTC

from admissions_agent.models import EmailMessage, EmailThread


def omnia_thread() -> EmailThread:
    return EmailThread(
        thread_id="omnia-1",
        snippet="Residence in Finland required for admission eligibility.",
        messages=[
            EmailMessage(
                message_id="m1",
                from_address="admissions@omnia.fi",
                subject="Eligibility update",
                body_text="Applicants must currently reside in Finland to be eligible.",
                sent_at=datetime(2026, 1, 15, tzinfo=UTC),
            )
        ],
    )


def p_porto_thread() -> EmailThread:
    return EmailThread(
        thread_id="porto-1",
        snippet="Thank you for your message.",
        messages=[
            EmailMessage(
                message_id="m2",
                from_address="info@ipp.pt",
                subject="Re: Application inquiry",
                body_text="This is a generic response. Please check the website.",
                sent_at=datetime(2026, 2, 10, tzinfo=UTC),
            )
        ],
    )


def fiu_thread() -> EmailThread:
    return EmailThread(
        thread_id="fiu-1",
        snippet="International applicants are not viable before 2027 except English prep.",
        messages=[
            EmailMessage(
                message_id="m3",
                from_address="admissions@fiu.example",
                subject="Program intake details",
                body_text="No general intake before 2027; only English preparation is possible.",
                sent_at=datetime(2026, 3, 4, tzinfo=UTC),
            )
        ],
    )
