from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from admissions_agent.models import EmailMessage, EmailThread


class GmailClientProtocol(Protocol):
    def search_candidate_threads(self, query: str) -> list[str]:
        ...

    def fetch_thread(self, thread_id: str) -> EmailThread:
        ...

    def add_label(self, thread_id: str, label_name: str) -> None:
        ...

    def get_history_since(self, history_id: str) -> dict:
        ...


@dataclass(slots=True)
class CandidateFilterRules:
    sender_allowlist: set[str] = field(default_factory=set)
    domain_allowlist: set[str] = field(default_factory=set)
    admissions_keywords: dict[str, int] = field(
        default_factory=lambda: {
            "admission": 3,
            "apply": 2,
            "application": 3,
            "eligibility": 2,
            "enrollment": 2,
            "intake": 2,
            "deadline": 2,
            "program": 1,
            "tuition": 1,
            "scholarship": 1,
        }
    )
    negative_keywords: dict[str, int] = field(
        default_factory=lambda: {
            "newsletter": 3,
            "promo": 3,
            "unsubscribe": 4,
            "discount": 2,
            "sales": 2,
            "invoice": 2,
            "timesheet": 2,
            "meeting": 2,
            "jira": 2,
            "standup": 2,
            "benefits": 2,
        }
    )
    minimum_score: int = 2
    reply_thread_boost: int = 2


@dataclass(slots=True)
class CandidateScore:
    thread_id: str
    score: int
    minimum_score: int
    allowlist_match: bool
    admissions_hits: list[str]
    negative_hits: list[str]
    reply_boost_applied: bool

    @property
    def is_candidate(self) -> bool:
        return self.allowlist_match and self.score >= self.minimum_score


class ThreadCandidateFilter:
    def __init__(self, rules: CandidateFilterRules | None = None) -> None:
        self.rules = rules or CandidateFilterRules()

    def update_rules(self, rules: CandidateFilterRules) -> None:
        self.rules = rules

    def score_thread(self, thread: EmailThread, is_reply_to_existing_thread: bool) -> CandidateScore:
        allowlist_match = self._matches_allowlist(thread)
        text = self._thread_text(thread)

        score = 0
        admissions_hits: list[str] = []
        for keyword, weight in self.rules.admissions_keywords.items():
            if keyword in text:
                admissions_hits.append(keyword)
                score += weight

        negative_hits: list[str] = []
        for keyword, weight in self.rules.negative_keywords.items():
            if keyword in text:
                negative_hits.append(keyword)
                score -= weight

        reply_boost_applied = False
        if is_reply_to_existing_thread:
            score += self.rules.reply_thread_boost
            reply_boost_applied = True

        if not allowlist_match:
            score -= self.rules.minimum_score

        return CandidateScore(
            thread_id=thread.thread_id,
            score=score,
            minimum_score=self.rules.minimum_score,
            allowlist_match=allowlist_match,
            admissions_hits=admissions_hits,
            negative_hits=negative_hits,
            reply_boost_applied=reply_boost_applied,
        )

    def _thread_text(self, thread: EmailThread) -> str:
        parts = [thread.snippet]
        for msg in thread.messages:
            parts.extend([msg.subject, msg.body_text, msg.from_address])
        return " ".join(parts).lower()

    def _matches_allowlist(self, thread: EmailThread) -> bool:
        if not self.rules.sender_allowlist and not self.rules.domain_allowlist:
            return True

        exact_sender_matches = {
            msg.from_address.strip().lower() for msg in thread.messages if msg.from_address
        }
        if self.rules.sender_allowlist.intersection(exact_sender_matches):
            return True

        for sender in exact_sender_matches:
            if "@" not in sender:
                continue
            domain = sender.split("@", 1)[1]
            if domain in self.rules.domain_allowlist:
                return True
        return False


class GmailClient:
    """Gmail integration wrapper with candidate filtering."""

    def __init__(
        self,
        service=None,
        user_id: str = "me",
        candidate_filter: ThreadCandidateFilter | None = None,
        known_thread_ids: set[str] | None = None,
        max_search_results: int = 100,
    ) -> None:
        self.user_id = user_id
        self.service = service
        self.candidate_filter = candidate_filter or ThreadCandidateFilter()
        self.known_thread_ids = known_thread_ids or set()
        self.max_search_results = max_search_results

    @staticmethod
    def rules_from_dict(raw_rules: dict | None) -> CandidateFilterRules:
        raw_rules = raw_rules or {}

        def _as_int_map(values: dict | None) -> dict[str, int]:
            if not values:
                return {}
            out: dict[str, int] = {}
            for key, value in values.items():
                try:
                    out[str(key).strip().lower()] = int(value)
                except (TypeError, ValueError):
                    continue
            return out

        base_rules = CandidateFilterRules()

        admissions_keywords = _as_int_map(raw_rules.get("admissions_keywords"))
        negative_keywords = _as_int_map(raw_rules.get("negative_keywords"))

        return CandidateFilterRules(
            sender_allowlist={str(v).strip().lower() for v in raw_rules.get("sender_allowlist", []) if v},
            domain_allowlist={str(v).strip().lower() for v in raw_rules.get("domain_allowlist", []) if v},
            admissions_keywords=admissions_keywords or base_rules.admissions_keywords,
            negative_keywords=negative_keywords or base_rules.negative_keywords,
            minimum_score=int(raw_rules.get("minimum_score", base_rules.minimum_score)),
            reply_thread_boost=int(raw_rules.get("reply_thread_boost", base_rules.reply_thread_boost)),
        )

    def update_rules(self, rules: CandidateFilterRules) -> None:
        self.candidate_filter.update_rules(rules)

    def search_candidate_threads(self, query: str) -> list[str]:
        response = (
            self._service().users()
            .messages()
            .list(userId=self.user_id, q=query, maxResults=self.max_search_results)
            .execute()
        )
        message_refs = response.get("messages", [])
        unique_thread_ids = {item["threadId"] for item in message_refs if item.get("threadId")}

        scored_candidates: list[CandidateScore] = []
        for thread_id in unique_thread_ids:
            thread = self.fetch_thread(thread_id)
            score = self.candidate_filter.score_thread(
                thread,
                is_reply_to_existing_thread=(thread_id in self.known_thread_ids or len(thread.messages) > 1),
            )
            if score.is_candidate:
                scored_candidates.append(score)

        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return [candidate.thread_id for candidate in scored_candidates]

    def fetch_thread(self, thread_id: str) -> EmailThread:
        payload = (
            self._service()
            .users()
            .threads()
            .get(userId=self.user_id, id=thread_id, format="full")
            .execute()
        )
        messages: list[EmailMessage] = []
        for raw_message in payload.get("messages", []):
            headers = {
                header.get("name", "").lower(): header.get("value", "")
                for header in raw_message.get("payload", {}).get("headers", [])
            }
            internal_date_ms = int(raw_message.get("internalDate", "0") or "0")
            sent_at = datetime.fromtimestamp(internal_date_ms / 1000, tz=UTC)
            body_text = self._extract_message_text(raw_message.get("payload", {}))
            messages.append(
                EmailMessage(
                    message_id=raw_message.get("id", ""),
                    from_address=headers.get("from", ""),
                    subject=headers.get("subject", ""),
                    body_text=body_text,
                    sent_at=sent_at,
                    labels=raw_message.get("labelIds", []),
                )
            )

        return EmailThread(thread_id=payload.get("id", thread_id), snippet=payload.get("snippet", ""), messages=messages)

    def add_label(self, thread_id: str, label_name: str) -> None:
        label_id = self._get_or_create_label_id(label_name)
        (
            self._service().users()
            .threads()
            .modify(
                userId=self.user_id,
                id=thread_id,
                body={"addLabelIds": [label_id], "removeLabelIds": []},
            )
            .execute()
        )

    def get_history_since(self, history_id: str) -> dict:
        return (
            self._service().users()
            .history()
            .list(userId=self.user_id, startHistoryId=history_id, historyTypes=["messageAdded"])
            .execute()
        )

    def fetch_new_threads(self) -> list[EmailThread]:
        default_query = os.getenv(
            "GMAIL_SEARCH_QUERY",
            "newer_than:7d -category:promotions -category:social",
        )
        thread_ids = self.search_candidate_threads(default_query)
        return [self.fetch_thread(thread_id) for thread_id in thread_ids]

    def _get_or_create_label_id(self, label_name: str) -> str:
        labels_response = self._service().users().labels().list(userId=self.user_id).execute()
        for label in labels_response.get("labels", []):
            if label.get("name") == label_name:
                return label["id"]

        created_label = (
            self._service().users()
            .labels()
            .create(
                userId=self.user_id,
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        return created_label["id"]

    def _extract_message_text(self, payload: dict) -> str:
        mime_type = payload.get("mimeType", "")
        body = payload.get("body", {})
        if mime_type == "text/plain" and body.get("data"):
            return self._decode_base64_text(body["data"])

        texts: list[str] = []
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                texts.append(self._decode_base64_text(part["body"]["data"]))
        if texts:
            return "\n".join(texts)

        if body.get("data"):
            return self._decode_base64_text(body["data"])
        return ""

    def _decode_base64_text(self, value: str) -> str:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")

    def _build_service_from_env(self):
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        client_id = os.getenv("GMAIL_CLIENT_ID")
        client_secret = os.getenv("GMAIL_CLIENT_SECRET")
        refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            raise RuntimeError("Missing Gmail OAuth credentials in environment")

        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.modify"],
        )
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def _service(self):
        if self.service is None:
            self.service = self._build_service_from_env()
        return self.service
