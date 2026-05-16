from admissions_agent.enums import EligibilityStatus, MessageType
from admissions_agent.models import ClassifierResult, EmailThread, InstitutionCandidate


class ThreadClassifier:
    """Deterministic placeholder classifier."""

    def classify(self, thread: EmailThread) -> ClassifierResult:
        text = " ".join(
            [thread.snippet, *[m.subject + " " + m.body_text for m in thread.messages]]
        ).lower()
        message_type = MessageType.ADMISSIONS
        if "newsletter" in text or "promo" in text:
            message_type = MessageType.MARKETING
        elif any(token in text for token in ("auto-reply", "out of office", "automatic reply")):
            message_type = MessageType.AUTO_REPLY

        return ClassifierResult(
            thread_id=thread.thread_id,
            message_type=message_type,
            eligibility_status=EligibilityStatus.UNKNOWN,
            institution=InstitutionCandidate(
                canonical_name="Unknown Institution",
                source_value="",
                confidence=0.0,
                is_known=False,
            ),
            notes="Skeleton classifier result",
        )
