from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any, Protocol

from admissions_agent.models import ProposedPatch


class SheetsClientProtocol(Protocol):
    def load_applications(self) -> list[dict[str, str]]:
        ...

    def load_email_rules(self) -> dict[str, Any]:
        ...

    def append_review_queue(self, payload: dict[str, Any]) -> None:
        ...

    def append_agent_log(self, payload: dict[str, Any]) -> None:
        ...

    def apply_patch_to_application(self, patch: ProposedPatch) -> dict[str, Any]:
        ...


class SheetsClient:
    """Google Sheets integration adapter."""

    def __init__(
        self,
        service=None,
        spreadsheet_id: str | None = None,
        applications_sheet: str | None = None,
        rules_sheet: str | None = None,
        review_queue_sheet: str | None = None,
        agent_log_sheet: str | None = None,
    ) -> None:
        self.service = service
        self.spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")

        self.applications_sheet = applications_sheet or os.getenv(
            "GOOGLE_SHEETS_APPLICATIONS_WORKSHEET_NAME",
            os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Applications"),
        )
        self.rules_sheet = rules_sheet or os.getenv("GOOGLE_SHEETS_RULES_WORKSHEET_NAME", "EmailRules")
        self.review_queue_sheet = review_queue_sheet or os.getenv(
            "GOOGLE_SHEETS_REVIEW_QUEUE_WORKSHEET_NAME", "ReviewQueue"
        )
        self.agent_log_sheet = agent_log_sheet or os.getenv(
            "GOOGLE_SHEETS_AGENT_LOG_WORKSHEET_NAME", "AgentLog"
        )

    def load_applications(self) -> list[dict[str, str]]:
        values = self._read_range(f"{self.applications_sheet}!A:Z")
        if not values:
            return []
        headers = [str(h).strip() for h in values[0]]
        rows = values[1:]

        out: list[dict[str, str]] = []
        for row in rows:
            mapped: dict[str, str] = {}
            for idx, header in enumerate(headers):
                mapped[header] = str(row[idx]).strip() if idx < len(row) else ""
            out.append(mapped)
        return out

    def load_email_rules(self) -> dict[str, Any]:
        values = self._read_range(f"{self.rules_sheet}!A:Z")
        if not values:
            return {
                "sender_allowlist": [],
                "domain_allowlist": [],
                "admissions_keywords": {},
                "negative_keywords": {},
            }

        headers = [self._normalize_key(h) for h in values[0]]
        payload = {
            "sender_allowlist": [],
            "domain_allowlist": [],
            "admissions_keywords": {},
            "negative_keywords": {},
        }

        for row in values[1:]:
            raw = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            enabled = str(raw.get("enabled", "true")).strip().lower() not in {"false", "0", "no"}
            if not enabled:
                continue

            rule_type = self._normalize_key(str(raw.get("rule_type", raw.get("type", ""))))
            value = str(raw.get("value", "")).strip()
            if not rule_type or not value:
                continue

            weight = self._safe_int(raw.get("weight"), default=1)
            if rule_type == "sender_allowlist":
                payload["sender_allowlist"].append(value.lower())
            elif rule_type == "domain_allowlist":
                payload["domain_allowlist"].append(value.lower())
            elif rule_type == "admissions_keyword":
                payload["admissions_keywords"][value.lower()] = weight
            elif rule_type == "negative_keyword":
                payload["negative_keywords"][value.lower()] = weight
            elif rule_type == "minimum_score":
                payload["minimum_score"] = weight
            elif rule_type == "reply_thread_boost":
                payload["reply_thread_boost"] = weight

        return payload

    def append_review_queue(self, payload: dict[str, Any]) -> None:
        row = [
            datetime.now(tz=UTC).isoformat(),
            payload.get("thread_id", ""),
            payload.get("reason", ""),
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
        ]
        self._append_row(f"{self.review_queue_sheet}!A:D", row)

    def append_agent_log(self, payload: dict[str, Any]) -> None:
        row = [
            datetime.now(tz=UTC).isoformat(),
            payload.get("event", ""),
            payload.get("thread_id", ""),
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
        ]
        self._append_row(f"{self.agent_log_sheet}!A:D", row)

    def apply_patch_to_application(self, patch: ProposedPatch) -> dict[str, Any]:
        values = self._read_range(f"{self.applications_sheet}!A:Z")
        if not values:
            raise RuntimeError("Applications sheet is empty; cannot apply patch safely")

        headers = [str(h).strip() for h in values[0]]
        rows = values[1:]
        row_idx, old_row = self._find_application_row(rows, headers, patch.institution_name)

        updated_row, changed_columns = self._build_application_row_patch(headers, old_row, patch)
        sheet_row_number = row_idx + 2
        end_column = self._column_letter(len(headers))
        update_range = f"{self.applications_sheet}!A{sheet_row_number}:{end_column}{sheet_row_number}"

        self._service().spreadsheets().values().update(
            spreadsheetId=self._spreadsheet_id(),
            range=update_range,
            valueInputOption="USER_ENTERED",
            body={"values": [updated_row]},
        ).execute()

        return {
            "updated": True,
            "sheet_row": sheet_row_number,
            "changed_columns": changed_columns,
            "institution": patch.institution_name,
        }

    def _find_application_row(
        self,
        rows: list[list[Any]],
        headers: list[str],
        institution_name: str,
    ) -> tuple[int, list[str]]:
        header_index = self._header_index_map(headers)
        institution_idx = self._pick_header_index(
            header_index, ["institution_name", "institution", "university", "school"]
        )
        if institution_idx is None:
            raise RuntimeError("Applications sheet must include an institution column")

        target = institution_name.strip().lower()
        for idx, row in enumerate(rows):
            row_value = str(row[institution_idx]).strip().lower() if institution_idx < len(row) else ""
            if row_value == target:
                normalized = [str(row[i]).strip() if i < len(row) else "" for i in range(len(headers))]
                return idx, normalized
        raise RuntimeError(f"Could not find application row for institution: {institution_name}")

    @staticmethod
    def _build_application_row_patch(
        headers: list[str],
        existing_row: list[str],
        patch: ProposedPatch,
    ) -> tuple[list[str], list[str]]:
        updated_row = list(existing_row)
        normalized_headers = {SheetsClient._normalize_key(name): idx for idx, name in enumerate(headers)}

        changed: list[str] = []
        mapping = {
            "eligibility_status": patch.proposed_status.eligibility_status,
            "application_status": patch.proposed_status.application_status,
        }

        for key, value in mapping.items():
            if value is None:
                continue
            idx = normalized_headers.get(key)
            if idx is None:
                continue
            new_value = str(value)
            if idx >= len(updated_row):
                updated_row.extend([""] * (idx + 1 - len(updated_row)))
            if updated_row[idx] != new_value:
                updated_row[idx] = new_value
                changed.append(headers[idx])

        reason_idx = normalized_headers.get("last_agent_reason")
        if reason_idx is not None:
            if reason_idx >= len(updated_row):
                updated_row.extend([""] * (reason_idx + 1 - len(updated_row)))
            updated_row[reason_idx] = patch.reason
            changed.append(headers[reason_idx])

        return updated_row, changed

    def _read_range(self, a1_range: str) -> list[list[Any]]:
        response = (
            self._service().spreadsheets()
            .values()
            .get(spreadsheetId=self._spreadsheet_id(), range=a1_range)
            .execute()
        )
        return response.get("values", [])

    def _append_row(self, a1_range: str, row: list[Any]) -> None:
        self._service().spreadsheets().values().append(
            spreadsheetId=self._spreadsheet_id(),
            range=a1_range,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

    @staticmethod
    def _normalize_key(value: str) -> str:
        return str(value).strip().lower().replace(" ", "_")

    @staticmethod
    def _safe_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _header_index_map(headers: list[str]) -> dict[str, int]:
        return {SheetsClient._normalize_key(name): idx for idx, name in enumerate(headers)}

    @staticmethod
    def _pick_header_index(header_map: dict[str, int], candidates: list[str]) -> int | None:
        for candidate in candidates:
            idx = header_map.get(candidate)
            if idx is not None:
                return idx
        return None

    @staticmethod
    def _column_letter(index: int) -> str:
        if index <= 0:
            return "A"
        out = ""
        n = index
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            out = chr(65 + remainder) + out
        return out

    def _build_service_from_env(self):
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        service_account_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH")
        if not service_account_path:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON_PATH is required")

        credentials = Credentials.from_service_account_file(
            service_account_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        return build("sheets", "v4", credentials=credentials, cache_discovery=False)

    def _spreadsheet_id(self) -> str:
        if not self.spreadsheet_id:
            raise RuntimeError("GOOGLE_SHEETS_SPREADSHEET_ID is required")
        return self.spreadsheet_id

    def _service(self):
        if self.service is None:
            self.service = self._build_service_from_env()
        return self.service
