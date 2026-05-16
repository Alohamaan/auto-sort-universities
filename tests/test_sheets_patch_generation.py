from admissions_agent.enums import ApplicationStatus, EligibilityStatus
from admissions_agent.models import ProposedPatch, ProposedStatus
from admissions_agent.sheets import SheetsClient


def test_build_application_row_patch_updates_statuses_and_reason() -> None:
    headers = ["institution_name", "eligibility_status", "application_status", "last_agent_reason"]
    existing = ["Omnia", "unknown", "not_started", ""]
    patch = ProposedPatch(
        institution_name="Omnia",
        reason="Eligibility confirmed by admissions office",
        proposed_status=ProposedStatus(
            eligibility_status=EligibilityStatus.ELIGIBLE,
            application_status=ApplicationStatus.IN_PROGRESS,
        ),
    )

    updated_row, changed = SheetsClient._build_application_row_patch(headers, existing, patch)

    assert updated_row == [
        "Omnia",
        "eligible",
        "in_progress",
        "Eligibility confirmed by admissions office",
    ]
    assert changed == ["eligibility_status", "application_status", "last_agent_reason"]


def test_build_application_row_patch_skips_missing_columns_gracefully() -> None:
    headers = ["institution_name", "eligibility_status"]
    existing = ["FIU", "unknown"]
    patch = ProposedPatch(
        institution_name="FIU",
        reason="No general intake before 2027",
        proposed_status=ProposedStatus(application_status=ApplicationStatus.REJECTED),
    )

    updated_row, changed = SheetsClient._build_application_row_patch(headers, existing, patch)

    assert updated_row == existing
    assert changed == []
