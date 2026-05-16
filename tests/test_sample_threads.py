from admissions_agent.decision_engine import DecisionEngine
from admissions_agent.enums import ApplicationStatus, DecisionKind, EligibilityStatus, MessageType
from admissions_agent.models import ClassifierResult, InstitutionCandidate
from tests.fixtures.threads import fiu_thread, omnia_thread, p_porto_thread


engine = DecisionEngine()


def test_omnia_not_viable_finland_requirement() -> None:
    thread = omnia_thread()
    result = ClassifierResult(
        thread_id=thread.thread_id,
        message_type=MessageType.ADMISSIONS,
        eligibility_status=EligibilityStatus.NOT_ELIGIBLE,
        application_status=ApplicationStatus.NOT_STARTED,
        institution=InstitutionCandidate(canonical_name="Omnia", source_value="omnia.fi", confidence=0.98),
        notes="Residence in Finland required",
    )
    decision = engine.decide(result)
    assert decision.kind == DecisionKind.PENDING_ACTION


def test_p_porto_generic_reply_needs_manual_review() -> None:
    thread = p_porto_thread()
    result = ClassifierResult(
        thread_id=thread.thread_id,
        message_type=MessageType.ADMISSIONS,
        institution=InstitutionCandidate(
            canonical_name="P.PORTO",
            source_value="ipp.pt",
            confidence=0.55,
            is_known=False,
        ),
        notes="Generic reply; not enough evidence",
    )
    decision = engine.decide(result)
    assert decision.kind == DecisionKind.REVIEW_QUEUE


def test_fiu_not_viable_before_2027_except_english_prep() -> None:
    thread = fiu_thread()
    result = ClassifierResult(
        thread_id=thread.thread_id,
        message_type=MessageType.ADMISSIONS,
        eligibility_status=EligibilityStatus.NOT_ELIGIBLE,
        institution=InstitutionCandidate(
            canonical_name="Final International University",
            source_value="fiu.example",
            confidence=0.9,
            is_known=True,
        ),
        notes="Not viable before 2027 except English prep",
    )
    decision = engine.decide(result)
    assert decision.kind == DecisionKind.PENDING_ACTION
