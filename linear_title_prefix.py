"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

STATUS_UPDATE_TRIGGERS = {
    "statuschange",
    "statuschanged",
    "statusupdated",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
ISSUE_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to research.

    The Cursor automation trigger provides a compact ``triggerContext`` payload,
    while Linear webhooks often place issue fields under ``data`` or ``issue``.
    This function accepts those common shapes and stays side-effect free so the
    caller can decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    context = _payload_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_label(status) != _normalize_label(RESEARCH_STATUS):
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the payload while allowing issue data to override envelope data."""

    context: dict[str, Any] = dict(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        context.update(data)

        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        normalized
        for key in ("trigger", "webhookType", "action", "type")
        if (normalized := _normalize_label(_text_or_name(context.get(key))))
    ]

    if any(value in STATUS_UPDATE_TRIGGERS for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    return any(
        _normalize_label(str(field)) in STATUS_FIELD_NAMES
        for field in _updated_field_names(context)
    )


def _updated_field_names(context: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("updatedFields", "updated_fields"):
        value = context.get(key)
        if isinstance(value, str):
            yield from re.split(r"[\s,;]+", value)
        elif isinstance(value, Mapping):
            yield from value.keys()
        elif isinstance(value, Iterable) and not isinstance(value, (bytes, str)):
            yield from value

    updated_from = context.get("updatedFrom")
    if updated_from is None:
        updated_from = context.get("updated_from")
    if isinstance(updated_from, Mapping):
        yield from updated_from.keys()


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        text = _text_or_name(context.get(key))
        if text:
            return text

    for key in ("status", "state", "workflowState", "workflow_state"):
        text = _text_or_name(context.get(key))
        if text:
            return text

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _text_or_name(context.get(key))
        if text:
            return text
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()

    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", with_spaces.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
