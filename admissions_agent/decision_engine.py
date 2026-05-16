from admissions_agent.enums import (
    ApplicationStatus,
    DecisionKind,
    MessageType,
    PendingActionType,
)
from admissions_agent.models import ClassifierResult, DecisionResult, PendingAction, ProposedPatch

STRONG_APPLICATION_STATUSES = {
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
}


class DecisionEngine:
    """Deterministic policy layer that gates all updates."""

    def decide(
        self,
        result: ClassifierResult,
        current_application_status: ApplicationStatus = ApplicationStatus.UNKNOWN,
    ) -> DecisionResult:
        if result.message_type == MessageType.MARKETING:
            return DecisionResult(kind=DecisionKind.IGNORE, reason="Marketing-only message")

        if result.message_type == MessageType.AUTO_REPLY:
            return DecisionResult(
                kind=DecisionKind.IGNORE, reason="Auto-reply ignored for eligibility"
            )

        if not result.institution or not result.institution.is_known:
            return DecisionResult(
                kind=DecisionKind.REVIEW_QUEUE,
                reason="Unknown institution; send to review queue",
                review_payload={"thread_id": result.thread_id, "notes": result.notes},
            )

        if (
            current_application_status in STRONG_APPLICATION_STATUSES
            and result.application_status
            not in {ApplicationStatus.UNKNOWN, current_application_status}
        ):
            return DecisionResult(
                kind=DecisionKind.IGNORE,
                reason="Blocked overwrite of strong application status",
            )

        patch = ProposedPatch(
            institution_name=result.institution.canonical_name,
            reason=result.notes or "Classifier proposed status update",
            proposed_status={
                "eligibility_status": result.eligibility_status,
                "application_status": result.application_status,
            },
            metadata={"thread_id": result.thread_id},
        )
        pending = PendingAction(
            action_id=f"pa-{result.thread_id}",
            action_type=PendingActionType.APPROVE_PATCH,
            thread_id=result.thread_id,
            patch=patch,
            prompt="Approve admissions tracker status update?",
        )
        return DecisionResult(
            kind=DecisionKind.PENDING_ACTION,
            reason="Eligibility/application change requires manual approval",
            pending_action=pending,
        )
