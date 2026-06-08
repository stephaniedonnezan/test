"""Build Linear issue title updates for research status changes.

The automation runner can call :func:`build_issue_title_update` with the JSON
payload from a Linear status-change event. When the issue moves to
"To Research", the function returns a small action object describing the title
update that should be applied.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TITLE_PREFIX = f"{PREFIX}: "
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The returned action is intentionally transport-agnostic so the caller can
    decide how to apply it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    status = _new_status(event)
    if not _is_status_change_event(event) or _normalize(status) != "to research":
        return None

    issue_id = _first_text(event, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(event, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize(value)
        for payload in _payloads(event)
        for key in ("trigger", "action", "type", "webhookType", "webhook_type")
        for value in (payload.get(key),)
        if value is not None
    }

    if event_names & {"status changed", "status change", "statuschanged"}:
        return True

    generic_update = bool(
        event_names
        & {
            "update",
            "updated",
            "issue update",
            "issue updated",
            "updated issue",
            "issueupdated",
        }
    )
    return generic_update and _updated_status_fields(event)


def _updated_status_fields(event: Mapping[str, Any]) -> bool:
    for field in _changed_field_names(event):
        if _normalize(field) in STATUS_FIELD_NAMES:
            return True
    return False


def _changed_field_names(event: Mapping[str, Any]) -> Iterable[str]:
    for payload in _payloads(event):
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "fields",
        ):
            value = payload.get(key)
            yield from _field_names(value)

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            yield from changes.keys()
        else:
            yield from _field_names(changes)


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        yield from value.keys()
    elif isinstance(value, Iterable):
        for item in value:
            if isinstance(item, str):
                yield item
            elif isinstance(item, Mapping):
                name = item.get("name") or item.get("field") or item.get("key")
                if isinstance(name, str):
                    yield name


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    return _first_text(event, explicit_keys) or _first_text(event, fallback_keys)


def _first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for payload in _priority_payloads(event):
        for key in keys:
            value = _text_value(payload.get(key))
            if value:
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier", "key"):
            text = _text_value(value.get(key))
            if text:
                return text
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _priority_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payloads.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            payloads.append(data_issue)
        payloads.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payloads.append(issue)

    payloads.append(event)
    return payloads


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def collect(payload: Mapping[str, Any]) -> None:
        if id(payload) in seen:
            return
        seen.add(id(payload))
        payloads.append(payload)

        for key in ("triggerContext", "data", "issue"):
            child = payload.get(key)
            if isinstance(child, Mapping):
                collect(child)

    collect(event)
    return payloads


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
