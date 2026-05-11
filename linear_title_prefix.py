"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research.

    The automation trigger payloads used in this repo are intentionally small,
    while Linear webhook payloads can be nested. This function accepts both by
    reading status metadata from the outer payload and issue details from nested
    ``triggerContext``, ``data``, or ``issue`` objects.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_mappings(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_status(candidates)
    if _normalize_label(new_status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _extract_first_string(candidates, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_string(candidates, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for JavaScript-style automation naming."""

    return build_issue_title_update(event)


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload sections, ordered from most-specific to broadest."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    for container in (trigger_context, data, issue):
        if isinstance(container, Mapping):
            for key in ("issue", "data"):
                add(container.get(key))
            add(container)

    add(event)
    return candidates


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for candidate in candidates:
        for key in ("trigger", "action", "type", "webhookType"):
            normalized_trigger = _normalize_label(candidate.get(key))
            if normalized_trigger in {"status changed", "status change", "state changed", "workflow state changed"}:
                return True
            if normalized_trigger in {"issue updated", "updated issue", "update", "updated"}:
                saw_issue_update = True

    if saw_issue_update:
        return _updated_fields_include_status(candidates)

    return False


def _updated_fields_include_status(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = candidate.get(key)
            if isinstance(fields, str) and _field_name_indicates_status(fields):
                return True
            if isinstance(fields, Mapping) and any(_field_name_indicates_status(field) for field in fields):
                return True
            if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
                if any(_field_name_indicates_status(field) for field in fields):
                    return True
    return False


def _field_name_indicates_status(field: Any) -> bool:
    return isinstance(field, str) and _normalize_key(field) in STATUS_FIELD_NAMES


def _extract_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    direct_status = _extract_first_string(
        candidates,
        ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"),
    )
    if direct_status:
        return direct_status

    for candidate in candidates:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = candidate.get(key)
            if isinstance(value, Mapping):
                nested_name = _extract_first_string((value,), ("name", "title", "label"))
                if nested_name:
                    return nested_name

    direct_status = _extract_first_string(candidates, ("status",))
    if direct_status:
        return direct_status

    return None


def _extract_first_string(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize_label(value: str | None) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "", value.lower())


def main() -> int:
    """Read a JSON payload from stdin and print the title update action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(payload)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
