"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    Cursor automation trigger payloads are flat under ``triggerContext``, while
    Linear webhooks can place issue data under ``data`` or ``issue``. This helper
    reads the likely payload sections and returns ``None`` unless the event is a
    status transition into the "to research" state.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_mappings(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_status(candidates)
    if _normalize_label(new_status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _extract_first_string(candidates, ("issueId", "issue_id", "id", "identifier"))
    title = _extract_first_string(candidates, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_title_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints using handler naming."""

    return build_issue_title_update(event)


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload sections, ordered from most-specific to broadest."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    for container in (event.get("triggerContext"), event.get("data"), event.get("issue")):
        if isinstance(container, Mapping):
            add(container.get("issue"))
            add(container.get("data"))
            add(container)

    add(event)
    return candidates


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for candidate in candidates:
        for key in ("trigger", "action", "type", "eventType", "webhookType"):
            marker = _normalize_label(candidate.get(key))
            if marker in {
                "status changed",
                "status change",
                "state changed",
                "workflow state changed",
            }:
                return True
            if marker in {"issue updated", "updated issue", "issue update", "update", "updated"}:
                saw_issue_update = True

    return saw_issue_update and _updated_fields_include_status(candidates)


def _updated_fields_include_status(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = candidate.get(key)
            if _fields_include_status(fields):
                return True
    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _field_name_indicates_status(fields)

    if isinstance(fields, Mapping):
        return any(_field_name_indicates_status(field) for field in fields)

    if isinstance(fields, Iterable):
        return any(_field_name_indicates_status(field) for field in fields)

    return False


def _field_name_indicates_status(field: Any) -> bool:
    if isinstance(field, Mapping):
        field = field.get("name") or field.get("field") or field.get("key")
    if not isinstance(field, str):
        return False

    return _normalize_key(field) in _STATUS_FIELD_NAMES


def _extract_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    direct_status = _extract_first_string(
        candidates,
        ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"),
    )
    if direct_status is not None:
        return direct_status

    for candidate in candidates:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = candidate.get(key)
            if isinstance(value, Mapping):
                nested_status = _extract_first_string((value,), ("name", "title", "label"))
                if nested_status is not None:
                    return nested_status

    return _extract_first_string(candidates, ("status",))


def _extract_first_string(
    candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_label(value: Any) -> str:
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

    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
