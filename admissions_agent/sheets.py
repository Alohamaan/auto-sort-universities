from admissions_agent.models import ProposedPatch


class SheetsClient:
    """Stub interface for tracker updates. No real writes in skeleton."""

    def propose_patch(self, patch: ProposedPatch) -> dict:
        return {"accepted": True, "dry_run": True, "patch": patch.model_dump()}
