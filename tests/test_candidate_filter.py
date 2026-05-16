from datetime import UTC, datetime

from admissions_agent.gmail import CandidateFilterRules, ThreadCandidateFilter
from admissions_agent.models import EmailMessage, EmailThread


def _thread(thread_id: str, sender: str, subject: str, body: str, extra_message: bool = False) -> EmailThread:
    messages = [
        EmailMessage(
            message_id=f"{thread_id}-1",
            from_address=sender,
            subject=subject,
            body_text=body,
            sent_at=datetime(2026, 5, 1, tzinfo=UTC),
        )
    ]
    if extra_message:
        messages.append(
            EmailMessage(
                message_id=f"{thread_id}-2",
                from_address=sender,
                subject="Re: " + subject,
                body_text="Follow-up",
                sent_at=datetime(2026, 5, 2, tzinfo=UTC),
            )
        )

    return EmailThread(thread_id=thread_id, snippet=body, messages=messages)


def test_candidate_filter_accepts_allowlisted_sender_with_admissions_signal() -> None:
    rules = CandidateFilterRules(
        sender_allowlist={"admissions@uni.edu"},
        admissions_keywords={"admission": 3, "deadline": 2},
        negative_keywords={"newsletter": 3},
        minimum_score=2,
    )
    score = ThreadCandidateFilter(rules).score_thread(
        _thread("t1", "admissions@uni.edu", "Admission deadline", "Admission deadline update"),
        is_reply_to_existing_thread=False,
    )

    assert score.allowlist_match is True
    assert score.score >= 2
    assert score.is_candidate is True


def test_candidate_filter_rejects_non_allowlisted_sender() -> None:
    rules = CandidateFilterRules(
        sender_allowlist={"admissions@uni.edu"},
        admissions_keywords={"admission": 5},
        negative_keywords={},
        minimum_score=2,
    )
    score = ThreadCandidateFilter(rules).score_thread(
        _thread("t2", "random@other.edu", "Admission update", "Admission update available"),
        is_reply_to_existing_thread=False,
    )

    assert score.allowlist_match is False
    assert score.is_candidate is False


def test_candidate_filter_reply_boost_can_move_borderline_thread_to_candidate() -> None:
    rules = CandidateFilterRules(
        domain_allowlist={"uni.edu"},
        admissions_keywords={"apply": 1},
        negative_keywords={},
        minimum_score=2,
        reply_thread_boost=2,
    )
    filter_engine = ThreadCandidateFilter(rules)
    thread = _thread("t3", "office@uni.edu", "Apply now", "Apply", extra_message=True)

    without_reply = filter_engine.score_thread(thread, is_reply_to_existing_thread=False)
    with_reply = filter_engine.score_thread(thread, is_reply_to_existing_thread=True)

    assert without_reply.is_candidate is False
    assert with_reply.reply_boost_applied is True
    assert with_reply.is_candidate is True
