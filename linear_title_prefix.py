"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_payloads(event)
    if not _is_status_change_event(candidates):
        return None

    status = _first_text(_status_values(candidates))
    if _normalize(status) != TARGET_STATUS:
        return None

    identity_candidates = _identity_payloads(event, candidates)
    issue_id = _first_text(
        _field_values(identity_candidates, ("id", "issueId", "issue_id", "identifier", "key"))
    )
    title = _first_text(_field_values(identity_candidates, ("title", "name", "summary")))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title:
        return None

    if stripped_title.lower().startswith(PREFIX.lower()):
        prefixed_title = stripped_title
    else:
        prefixed_title = f"{PREFIX}: {stripped_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    add(event)
    for key in ("triggerContext", "data", "issue"):
        add(event.get(key))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("triggerContext"))

    return payloads


def _identity_payloads(
    event: Mapping[str, Any], fallback_payloads: list[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")

    if isinstance(data, Mapping):
        add(data.get("issue"))
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        nested_data = trigger_context.get("data")
        if isinstance(nested_data, Mapping):
            add(nested_data.get("issue"))
    add(event.get("issue"))
    add(trigger_context)
    add(data)
    add(event)
    for payload in fallback_payloads:
        add(payload)

    return payloads


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    trigger_values = _field_values(
        payloads, ("trigger", "webhookType", "action", "type", "eventType")
    )
    normalized_triggers = {_normalize(value) for value in trigger_values if _text(value)}
    if any(value in {"status changed", "status change", "status"} for value in normalized_triggers):
        return True

    update_triggers = {"update", "updated", "issue update", "issue updated", "updated issue"}
    if normalized_triggers & update_triggers:
        return _updated_status_field(payloads)

    return False


def _updated_status_field(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in ("updatedFields", "updated_fields"):
            fields = payload.get(key)
            if _contains_status_field(fields):
                return True

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(key) in STATUS_FIELD_NAMES for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_normalize(key) in STATUS_FIELD_NAMES for key in value)
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    return False


def _status_values(payloads: list[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    values.extend(
        _field_values(
            payloads,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
            ),
        )
    )

    for payload in payloads:
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _normalize(key) in STATUS_FIELD_NAMES:
                    if isinstance(value, Mapping):
                        values.extend(
                            _field_values([value], ("to", "newValue", "new_value", "name"))
                        )
                    else:
                        values.append(value)

    values.extend(
        _field_values(payloads, ("status", "state", "workflowState", "workflow_state"))
    )
    return values


def _field_values(payloads: list[Mapping[str, Any]], names: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for payload in payloads:
        for name in names:
            if name in payload:
                value = payload[name]
                if isinstance(value, Mapping):
                    values.extend(_field_values([value], ("name", "title", "id", "identifier", "key")))
                else:
                    values.append(value)
    return values


def _first_text(values: list[Any]) -> str | None:
    for value in values:
        text = _text(value)
        if text is not None and text.strip():
            return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return None


def _normalize(value: Any) -> str:
    text = _text(value)
    if text is None:
        return ""
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    collapsed = re.sub(r"[^a-zA-Z0-9]+", " ", with_spaces).strip().lower()
    return re.sub(r"\s+", " ", collapsed)


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
