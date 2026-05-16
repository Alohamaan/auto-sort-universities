from __future__ import annotations

import os
from typing import Any, Callable, Protocol

from admissions_agent.classifier import ThreadClassifier
from admissions_agent.decision_engine import DecisionEngine
from admissions_agent.enums import ApplicationStatus, DecisionKind
from admissions_agent.gmail import GmailClient, GmailClientProtocol
from admissions_agent.models import ClassifierResult, DecisionResult
from admissions_agent.sheets import SheetsClient, SheetsClientProtocol


class ClassifierProtocol(Protocol):
    def classify(self, thread) -> ClassifierResult:
        ...


class DecisionEngineProtocol(Protocol):
    def decide(
        self,
        result: ClassifierResult,
        current_application_status: ApplicationStatus = ApplicationStatus.UNKNOWN,
    ) -> DecisionResult:
        ...


class PollMailboxJob:
    def __init__(
        self,
        gmail: GmailClientProtocol | None = None,
        sheets: SheetsClientProtocol | None = None,
        classifier: ClassifierProtocol | None = None,
        engine: DecisionEngineProtocol | None = None,
        dry_run: bool = False,
        print_fn: Callable[[str], None] = print,
        default_query: str | None = None,
    ) -> None:
        self.gmail = gmail or GmailClient()
        self.sheets = sheets or SheetsClient()
        self.classifier = classifier or ThreadClassifier()
        self.engine = engine or DecisionEngine()
        self.dry_run = dry_run
        self.print_fn = print_fn
        self.default_query = default_query or os.getenv(
            "GMAIL_SEARCH_QUERY",
            "newer_than:7d -category:promotions -category:social",
        )
        self.review_label_name = os.getenv("GMAIL_REVIEW_LABEL_NAME", "admissions/review-queue")
        self.pending_label_name = os.getenv("GMAIL_PENDING_LABEL_NAME", "admissions/pending-action")

    def run_once(self, query: str | None = None) -> list[dict[str, Any]]:
        applications = self.sheets.load_applications()
        rules = self.sheets.load_email_rules()
        self._update_gmail_rules_if_supported(rules)

        search_query = query or self.default_query
        thread_ids = self.gmail.search_candidate_threads(search_query)

        outputs: list[dict[str, Any]] = []
        for thread_id in thread_ids:
            thread = self.gmail.fetch_thread(thread_id)
            classification = self.classifier.classify(thread)
            current_status = self._current_application_status(applications, classification)
            decision = self.engine.decide(classification, current_status)
            outputs.append(decision.model_dump())
            self._apply_decision_side_effects(thread_id, decision)

        return outputs

    def _update_gmail_rules_if_supported(self, rules: dict[str, Any]) -> None:
        if not hasattr(self.gmail, "update_rules"):
            return

        rules_from_dict = getattr(self.gmail, "rules_from_dict", None)
        if callable(rules_from_dict):
            parsed_rules = rules_from_dict(rules)
            self.gmail.update_rules(parsed_rules)

    def _current_application_status(
        self,
        applications: list[dict[str, str]],
        classification: ClassifierResult,
    ) -> ApplicationStatus:
        institution = classification.institution
        if not institution:
            return ApplicationStatus.UNKNOWN

        for row in applications:
            row_name = (
                row.get("institution_name")
                or row.get("Institution")
                or row.get("institution")
                or row.get("University")
                or row.get("university")
                or ""
            )
            if row_name.strip().lower() != institution.canonical_name.strip().lower():
                continue

            raw_status = (
                row.get("application_status")
                or row.get("ApplicationStatus")
                or row.get("Application Status")
                or ""
            ).strip()
            try:
                return ApplicationStatus(raw_status)
            except ValueError:
                return ApplicationStatus.UNKNOWN

        return ApplicationStatus.UNKNOWN

    def _apply_decision_side_effects(self, thread_id: str, decision: DecisionResult) -> None:
        if decision.kind == DecisionKind.REVIEW_QUEUE:
            payload = decision.review_payload or {"thread_id": thread_id, "reason": decision.reason}
            payload.setdefault("thread_id", thread_id)
            payload.setdefault("reason", decision.reason)
            self._write_or_dry_run("append_review_queue", payload)
            self._label_or_dry_run(thread_id, self.review_label_name)
            return

        if decision.kind == DecisionKind.PENDING_ACTION:
            pending_action = decision.pending_action
            payload = {
                "event": "pending_action",
                "thread_id": thread_id,
                "reason": decision.reason,
                "action_id": pending_action.action_id if pending_action else "",
                "action_type": str(pending_action.action_type) if pending_action else "",
                "patch": pending_action.patch.model_dump() if pending_action and pending_action.patch else {},
            }
            self._write_or_dry_run("append_agent_log", payload)
            self._label_or_dry_run(thread_id, self.pending_label_name)

    def _write_or_dry_run(self, method_name: str, payload: dict[str, Any]) -> None:
        if self.dry_run:
            self.print_fn(
                f"DRY-RUN: would call SheetsClient.{method_name} payload={payload}"
            )
            return

        method = getattr(self.sheets, method_name)
        method(payload)

    def _label_or_dry_run(self, thread_id: str, label_name: str) -> None:
        if self.dry_run:
            self.print_fn(
                f"DRY-RUN: would call GmailClient.add_label thread_id={thread_id} label={label_name}"
            )
            return
        self.gmail.add_label(thread_id, label_name)
