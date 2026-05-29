"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for research status changes."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    if _normalized_text(_new_status(payload)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook/automation nesting into one lookup payload."""
    payload: dict[str, Any] = {}

    for key in ("issue", "data"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        if _is_explicit_status_change(value):
            return True

    for key in ("trigger", "webhookType"):
        value = payload.get(key)
        if _normalized_token(value) == "issueupdated":
            return _updated_status_fields(payload)

    action = _normalized_token(payload.get("action"))
    if action in {"update", "updated", "issueupdated", "updatedissue"}:
        return _updated_status_fields(payload)

    return False


def _is_explicit_status_change(value: Any) -> bool:
    return _normalized_token(value) in {
        "statuschanged",
        "statuschange",
        "statusupdated",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            field_names = [fields]
        elif isinstance(fields, Mapping):
            field_names = fields.keys()
        elif isinstance(fields, Iterable):
            field_names = fields
        else:
            continue

        for field in field_names:
            if _normalized_field_name(field) in STATUS_FIELD_NAMES:
                return True

    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status"):
        value = payload.get(key)
        if value is not None:
            return _name_from_value(value)

    for key in ("state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if value is not None:
            return _name_from_value(value)

    return None


def _name_from_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if nested_value is not None:
                return nested_value
    return value


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalized_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", with_spaces.casefold()).strip()


def _normalized_token(value: Any) -> str:
    return _normalized_text(value).replace(" ", "")


def _normalized_field_name(value: Any) -> str:
    return _normalized_token(value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
