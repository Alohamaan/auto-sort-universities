from enum import StrEnum


class MessageType(StrEnum):
    ADMISSIONS = "admissions"
    MARKETING = "marketing"
    AUTO_REPLY = "auto_reply"
    UNKNOWN = "unknown"


class EligibilityStatus(StrEnum):
    UNKNOWN = "unknown"
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    REQUIRES_REVIEW = "requires_review"


class ApplicationStatus(StrEnum):
    UNKNOWN = "unknown"
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    OFFER = "offer"
    REJECTED = "rejected"


class DecisionKind(StrEnum):
    IGNORE = "ignore"
    REVIEW_QUEUE = "review_queue"
    PENDING_ACTION = "pending_action"


class PendingActionType(StrEnum):
    APPROVE_PATCH = "approve_patch"
    REVIEW_THREAD = "review_thread"
