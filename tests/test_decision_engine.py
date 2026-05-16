from admissions_agent.decision_engine import DecisionEngine
from admissions_agent.enums import ApplicationStatus, DecisionKind, EligibilityStatus, MessageType
from admissions_agent.models import ClassifierResult, InstitutionCandidate


def test_marketing_messages_are_rejected() -> None:
    result = ClassifierResult(
        thread_id="t1",
        message_type=MessageType.MARKETING,
        institution=InstitutionCandidate(canonical_name="X", source_value="X", confidence=0.9),
    )
    decision = DecisionEngine().decide(result)
    assert decision.kind == DecisionKind.IGNORE


def test_unknown_institution_goes_to_review_queue() -> None:
    result = ClassifierResult(
        thread_id="t2",
        message_type=MessageType.ADMISSIONS,
        institution=InstitutionCandidate(
            canonical_name="Unknown", source_value="U", confidence=0.2, is_known=False
        ),
    )
    decision = DecisionEngine().decide(result)
    assert decision.kind == DecisionKind.REVIEW_QUEUE


def test_strong_status_not_overwritten() -> None:
    result = ClassifierResult(
        thread_id="t3",
        message_type=MessageType.ADMISSIONS,
        application_status=ApplicationStatus.IN_PROGRESS,
        institution=InstitutionCandidate(canonical_name="Known", source_value="K", confidence=0.9),
    )
    decision = DecisionEngine().decide(
        result, current_application_status=ApplicationStatus.SUBMITTED
    )
    assert decision.kind == DecisionKind.IGNORE


def test_status_change_requires_manual_approval() -> None:
    result = ClassifierResult(
        thread_id="t4",
        message_type=MessageType.ADMISSIONS,
        eligibility_status=EligibilityStatus.NOT_ELIGIBLE,
        application_status=ApplicationStatus.IN_PROGRESS,
        institution=InstitutionCandidate(canonical_name="Known", source_value="K", confidence=0.95),
    )
    decision = DecisionEngine().decide(result)
    assert decision.kind == DecisionKind.PENDING_ACTION
    assert decision.pending_action is not None
