"""Build Linear issue title updates for Cursor research automation triggers."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflow state", "workflowstatus", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research.

    The Cursor automation payload used in production is flat under
    ``triggerContext``, while Linear webhook payloads often nest issue details
    under ``data`` or ``issue``. This function accepts both shapes.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_mappings(event))
    if not _is_status_change(mappings):
        return None

    new_status = _extract_status(mappings)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_string(mappings, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_string(mappings, ("title",))
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_TITLE_PREFIX}: {trimmed_title}",
    }


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _iter_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mappings(item)


def _is_status_change(mappings: list[Mapping[str, Any]]) -> bool:
    event_labels = [
        _normalize_label(value)
        for mapping in mappings
        for key, value in mapping.items()
        if key in {"trigger", "webhookType", "action", "type"} and isinstance(value, str)
    ]

    if any(label in {"status changed", "status change", "statuschanged"} for label in event_labels):
        return True

    if any(label in {"issue updated", "updated issue", "update", "updated"} for label in event_labels):
        return _updated_fields_include_status(mappings)

    return False


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        updated_fields = mapping.get("updatedFields") or mapping.get("updated_fields")
        if isinstance(updated_fields, str):
            fields = [updated_fields]
        elif isinstance(updated_fields, list):
            fields = updated_fields
        else:
            continue

        if any(_normalize_label(field) in _STATUS_FIELDS for field in fields if isinstance(field, str)):
            return True

    return False


def _extract_status(mappings: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _extract_string(
        mappings,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "status_name",
        ),
    )
    if explicit_status:
        return explicit_status

    for mapping in mappings:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, Mapping):
                status_name = _extract_string([value], ("name", "title", "key", "id"))
                if status_name:
                    return status_name

    return None


def _extract_string(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_TITLE_PREFIX.casefold())


def _normalize_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).casefold()
    return " ".join(normalized.split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
