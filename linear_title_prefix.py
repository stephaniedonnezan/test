"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    mappings = _collect_mappings(event)
    if not _is_status_change_event(mappings):
        return None

    status = _first_status_value(mappings)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_issue_id(mappings)
    title = _first_text(mappings, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect common Linear/automation payload layers in precedence order."""
    mappings: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "trigger_context", "webhook", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            mappings.append(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node", "object"):
            value = data.get(key)
            if isinstance(value, Mapping):
                mappings.append(value)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        for key in ("state", "status", "workflowState"):
            value = issue.get(key)
            if isinstance(value, Mapping):
                mappings.append(value)

    for mapping in list(mappings):
        for key in ("state", "status", "workflowState", "workflow_state"):
            value = mapping.get(key)
            if isinstance(value, Mapping):
                mappings.append(value)

    return mappings


def _is_status_change_event(mappings: Iterable[Mapping[str, Any]]) -> bool:
    action_values = []
    has_status_field_update = False

    for mapping in mappings:
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            value = mapping.get(key)
            if isinstance(value, str):
                action_values.append(_normalize(value))

        if _updated_fields_include_status(mapping.get("updatedFields")):
            has_status_field_update = True
        if _updated_fields_include_status(mapping.get("updated_fields")):
            has_status_field_update = True

    if any(
        value in {"status changed", "status change", "state changed", "workflow state changed"}
        for value in action_values
    ):
        return True

    return has_status_field_update and any(
        value in {"update", "updated", "issue updated", "updated issue"}
        for value in action_values
    )


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (bytes, Mapping)):
        fields = list(updated_fields)
    else:
        return False

    for field in fields:
        if isinstance(field, Mapping):
            field = field.get("name") or field.get("field") or field.get("key")
        if isinstance(field, str) and _normalize(field) in _STATUS_FIELD_NAMES:
            return True
    return False


def _first_status_value(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    return _first_text(mappings, explicit_keys) or _first_text(mappings, fallback_keys)


def _first_issue_id(mappings: Iterable[Mapping[str, Any]]) -> str | None:
    mappings = list(mappings)
    id_keys = ("id", "issueId", "issue_id", "identifier")

    for mapping in mappings:
        if _first_text((mapping,), ("title",)):
            issue_id = _first_text((mapping,), id_keys)
            if issue_id:
                return issue_id

    return _first_text(mappings, id_keys)


def _first_text(mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for mapping in mappings:
        for key in keys:
            if key in mapping:
                value = _text_value(mapping[key])
                if value:
                    return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_text((value,), ("name", "title", "label", "id"))
    return None


def _normalize(value: Any) -> str | None:
    text = _text_value(value)
    if text is None:
        return None

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
