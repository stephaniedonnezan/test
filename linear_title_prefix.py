"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
ISSUE_UPDATE_TRIGGERS = {"issueupdated", "updatedissue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    fields = _collect_fields(event)
    if not _is_status_change_event(fields):
        return None

    status = _extract_new_status(fields)
    if _normalize_label(status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _coerce_non_empty_string(_first_value(fields, ("id", "issueId", "issue_id", "identifier")))
    title = _coerce_non_empty_string(_first_value(fields, ("title", "name")))
    if issue_id is None or title is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_fields(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear automation wrappers while preserving outer metadata."""
    fields: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        for nested_key in ("triggerContext", "data", "issue"):
            nested = value.get(nested_key)
            if isinstance(nested, Mapping):
                visit(nested)

        state = value.get("state")
        if isinstance(state, Mapping) and state.get("name") is not None:
            fields.setdefault("state.name", state.get("name"))

        workflow_state = value.get("workflowState") or value.get("workflow_state")
        if isinstance(workflow_state, Mapping) and workflow_state.get("name") is not None:
            fields.setdefault("workflowState.name", workflow_state.get("name"))

        for key, nested in value.items():
            if isinstance(nested, Mapping):
                continue
            fields[key] = nested

    visit(event)
    return fields


def _is_status_change_event(fields: Mapping[str, Any]) -> bool:
    trigger_values = (
        _normalize_event_token(value)
        for value in (
            fields.get("trigger"),
            fields.get("webhookType"),
            fields.get("action"),
            fields.get("type"),
        )
    )
    trigger_values = {value for value in trigger_values if value}
    if trigger_values & STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & ISSUE_UPDATE_TRIGGERS:
        return _updated_fields_include_status(fields.get("updatedFields") or fields.get("updated_fields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        candidates = re.split(r"[,;\s]+", updated_fields)
    elif isinstance(updated_fields, Mapping):
        candidates = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        candidates = updated_fields
    else:
        return False

    return any(_normalize_field_name(candidate) in STATUS_FIELDS for candidate in candidates)


def _extract_new_status(fields: Mapping[str, Any]) -> Any:
    return _first_value(
        fields,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "status",
            "state.name",
            "workflowState.name",
        ),
    )


def _first_value(fields: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = fields.get(key)
        if value is not None:
            return value
    return None


def _coerce_non_empty_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_event_token(value: Any) -> str:
    return _normalize_label(value).replace(" ", "")


def _normalize_field_name(value: Any) -> str:
    return _normalize_event_token(value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
