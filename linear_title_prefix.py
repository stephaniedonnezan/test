"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research status.

    The automation trigger can provide a flat Cursor ``triggerContext`` payload or
    a nested Linear webhook payload. This function is intentionally side-effect
    free so the caller can decide how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _ordered_payloads(event)
    if not _is_status_change_trigger(payloads):
        return None

    status = _extract_status(payloads)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payloads, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(payloads, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title.strip()}",
    }


def _ordered_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue maps in priority order without duplicates."""

    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and all(value is not existing for existing in payloads):
            payloads.append(value)

    add(event.get("triggerContext"))
    add(event)
    add(event.get("data"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("data"))
    add(event.get("issue"))

    for payload in list(payloads):
        for key in ("issue", "data"):
            nested = payload.get(key)
            if isinstance(nested, Mapping):
                add(nested)

    return payloads


def _is_status_change_trigger(payloads: Iterable[Mapping[str, Any]]) -> bool:
    trigger_keys = (
        "trigger",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "eventType",
        "event_type",
    )
    saw_generic_update = False

    for payload in payloads:
        for key in trigger_keys:
            value = payload.get(key)
            if not isinstance(value, str):
                continue

            normalized = _normalize_text(value)
            compact = normalized.replace(" ", "")
            if "chang" in compact and (
                "status" in compact or "state" in compact or "workflowstate" in compact
            ):
                return True
            if compact in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}:
                saw_generic_update = True

    return saw_generic_update and _updated_fields_include_status(payloads)


def _updated_fields_include_status(payloads: Iterable[Mapping[str, Any]]) -> bool:
    field_keys = (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "changes",
        "changedProperties",
        "changed_properties",
    )

    for payload in payloads:
        for key in field_keys:
            if _contains_status_field(payload.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_field_name_is_status(name) for name in value.keys())
    if isinstance(value, str):
        return _field_name_is_status(value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _field_name_is_status(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    compact = _normalize_text(value).replace(" ", "")
    return any(compact == field or compact.startswith(field) for field in STATUS_FIELD_NAMES)


def _extract_status(payloads: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    return _first_string(payloads, explicit_keys) or _first_string(payloads, fallback_keys)


def _first_string(payloads: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            string = _string_value(value)
            if string:
                return string
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return " ".join(normalized.split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
