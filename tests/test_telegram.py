from admissions_agent.enums import EligibilityStatus, PendingActionType
from admissions_agent.models import PendingAction, ProposedPatch, ProposedStatus
from admissions_agent.telegram import render_pending_action


def test_telegram_renderer() -> None:
    action = PendingAction(
        action_id="pa-1",
        action_type=PendingActionType.APPROVE_PATCH,
        thread_id="thread-1",
        patch=ProposedPatch(
            institution_name="Omnia",
            reason="Detected eligibility requirement",
            proposed_status=ProposedStatus(eligibility_status=EligibilityStatus.NOT_ELIGIBLE),
        ),
        prompt="Approve?",
    )
    text, callbacks = render_pending_action(action)
    assert "Omnia" in text
    assert callbacks["approve"] == "approve:pa-1"
