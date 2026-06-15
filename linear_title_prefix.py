"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_EVENT_VALUES = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_VALUES = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The Cursor automation trigger passes a flat ``triggerContext`` object, while
    Linear webhooks commonly nest the issue under ``data`` or ``data.issue``.
    This helper accepts both without performing the external API update itself.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = list(_candidate_payloads(event))
    if not _is_status_change_event(payloads):
        return None

    status = _new_status(payloads)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(payloads, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payloads, ("title",))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/metadata mappings from most to least specific."""

    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    event_values = []
    for payload in payloads:
        event_values.extend(
            _normalize_token(payload.get(key))
            for key in ("trigger", "webhookType", "webhook_type", "action", "type")
            if payload.get(key) is not None
        )

    if any(value in STATUS_EVENT_VALUES for value in event_values):
        return True

    if any(value in GENERIC_UPDATE_VALUES for value in event_values):
        return _has_status_updated_field(payloads)

    return _has_status_updated_field(payloads)


def _has_status_updated_field(payloads: Iterable[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "changed",
        ):
            value = payload.get(key)
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize_token(key) in STATUS_FIELDS for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(payloads: Iterable[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        value = _first_nested_text(
            payload,
            (
                ("newStatus",),
                ("new_status",),
                ("statusName",),
                ("status_name",),
                ("stateName",),
                ("state_name",),
                ("workflowStateName",),
                ("workflow_state_name",),
                ("to", "name"),
                ("toState", "name"),
                ("to_state", "name"),
                ("newValue", "name"),
                ("new_value", "name"),
            ),
        )
        if value:
            return value

        for change_key in ("changes", "changed", "status", "state", "workflowState", "workflow_state"):
            value = _status_from_change_value(payload.get(change_key))
            if value:
                return value

    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if not isinstance(value, Mapping):
        return None

    direct = _first_nested_text(
        value,
        (
            ("newStatus",),
            ("new_status",),
            ("newValue",),
            ("new_value",),
            ("to",),
            ("after",),
            ("name",),
        ),
    )
    if direct:
        return direct

    for key in ("status", "state", "workflowState", "workflow_state"):
        nested = _status_from_change_value(value.get(key))
        if nested:
            return nested

    return None


def _first_text(payloads: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _first_nested_text(payload: Mapping[str, Any], paths: tuple[tuple[str, ...], ...]) -> str | None:
    for path in paths:
        current: Any = payload
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                current = None
                break
            current = current[key]
        if isinstance(current, str) and current.strip():
            return current.strip()
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel(value).strip().lower())


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel(value).lower())


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
