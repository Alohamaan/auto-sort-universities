from admissions_agent.models import PendingAction


def render_pending_action(action: PendingAction) -> tuple[str, dict[str, str]]:
    patch = action.patch
    if patch:
        text = (
            f"Action: {action.action_type}\n"
            f"Institution: {patch.institution_name}\n"
            f"Eligibility: {patch.proposed_status.eligibility_status}\n"
            f"Application: {patch.proposed_status.application_status}\n"
            f"Reason: {patch.reason}"
        )
    else:
        text = f"Action: {action.action_type}\nThread: {action.thread_id}\n{action.prompt}"

    callbacks = {
        "approve": f"approve:{action.action_id}",
        "reject": f"reject:{action.action_id}",
    }
    return text, callbacks
