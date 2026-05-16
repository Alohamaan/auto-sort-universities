from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from admissions_agent.enums import (
    ApplicationStatus,
    DecisionKind,
    EligibilityStatus,
    MessageType,
    PendingActionType,
)


class EmailMessage(BaseModel):
    message_id: str
    from_address: str
    subject: str
    body_text: str
    sent_at: datetime
    labels: list[str] = Field(default_factory=list)


class EmailThread(BaseModel):
    thread_id: str
    snippet: str = ""
    messages: list[EmailMessage] = Field(default_factory=list)


class InstitutionCandidate(BaseModel):
    canonical_name: str
    source_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    is_known: bool = True


class ClassifierResult(BaseModel):
    thread_id: str
    message_type: MessageType
    eligibility_status: EligibilityStatus = EligibilityStatus.UNKNOWN
    application_status: ApplicationStatus = ApplicationStatus.UNKNOWN
    institution: InstitutionCandidate | None = None
    notes: str = ""


class ProposedStatus(BaseModel):
    eligibility_status: EligibilityStatus | None = None
    application_status: ApplicationStatus | None = None


class ProposedPatch(BaseModel):
    institution_name: str
    reason: str
    proposed_status: ProposedStatus
    metadata: dict[str, Any] = Field(default_factory=dict)


class PendingAction(BaseModel):
    action_id: str
    action_type: PendingActionType
    thread_id: str
    patch: ProposedPatch | None = None
    prompt: str


class DecisionResult(BaseModel):
    kind: DecisionKind
    reason: str
    pending_action: PendingAction | None = None
    review_payload: dict[str, Any] | None = None
