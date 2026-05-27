"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschange",
    "statuschanged",
    "statusupdate",
    "statusupdated",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_ISSUE_UPDATE_EVENTS = {
    "issueupdate",
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The Cursor automation trigger supplies a flat ``triggerContext`` payload, while
    Linear webhooks commonly nest issue details under ``data`` or ``issue``.
    This function accepts both shapes and returns a small action object for the
    caller to apply through its Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_mappings(event))
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_status(new_status) != _normalize_status(RESEARCH_STATUS):
        return None

    issue_id = _first_text_value(
        candidates,
        ("id", "issueId", "issue_id", "identifier"),
    )
    title = _first_text_value(candidates, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        new_title = stripped_title
    else:
        new_title = f"{TITLE_PREFIX}: {stripped_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": new_title,
    }


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload maps from most specific trigger context outward."""

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        yield trigger_context

    automation_info = _mapping_at(event, "automation_trigger_info")
    automation_context = _mapping_at(automation_info, "triggerContext")
    if automation_context:
        yield automation_context

    yield event

    data = _mapping_at(event, "data")
    if data:
        yield data
        data_issue = _mapping_at(data, "issue")
        if data_issue:
            yield data_issue

    issue = _mapping_at(event, "issue")
    if issue:
        yield issue

    if trigger_context:
        trigger_data = _mapping_at(trigger_context, "data")
        if trigger_data:
            yield trigger_data
            trigger_issue = _mapping_at(trigger_data, "issue")
            if trigger_issue:
                yield trigger_issue
        trigger_issue = _mapping_at(trigger_context, "issue")
        if trigger_issue:
            yield trigger_issue


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    event_values = []
    for candidate in candidates:
        for key in ("trigger", "event", "action", "type", "webhookType", "webhook_type"):
            value = candidate.get(key)
            if isinstance(value, str):
                event_values.append(_normalize_token(value))

    if any(value in _DIRECT_STATUS_CHANGE_TRIGGERS for value in event_values):
        return True

    if any(value in _ISSUE_UPDATE_EVENTS for value in event_values):
        return _updated_fields_include_status(candidates)

    return _updated_fields_include_status(candidates)


def _updated_fields_include_status(candidates: list[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_includes_status(candidate.get(key)):
                return True
    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        return any(_normalize_token(str(key)) in _STATUS_FIELD_NAMES for key in fields)

    if isinstance(fields, str):
        return _normalize_token(fields) in _STATUS_FIELD_NAMES

    if isinstance(fields, Iterable):
        for field in fields:
            if isinstance(field, Mapping):
                names = (
                    field.get("name"),
                    field.get("field"),
                    field.get("fieldName"),
                    field.get("field_name"),
                )
                if any(_normalize_token(str(name)) in _STATUS_FIELD_NAMES for name in names if name):
                    return True
            elif _normalize_token(str(field)) in _STATUS_FIELD_NAMES:
                return True

    return False


def _extract_new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text_value(
        candidates,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "newState",
            "new_state",
            "toState",
            "to_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if explicit_status:
        return explicit_status

    for candidate in candidates:
        status = _text_from_value(candidate.get("status"))
        if status:
            return status

        state = _text_from_value(candidate.get("state"))
        if state:
            return state

        workflow_state = _text_from_value(candidate.get("workflowState"))
        if workflow_state:
            return workflow_state

    return None


def _first_text_value(candidates: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = _text_from_value(candidate.get(key))
            if value:
                return value
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested = _text_from_value(value.get(key))
            if nested:
                return nested

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: str | None) -> str | None:
    if not value:
        return None
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.lower().split())


def _normalize_token(value: str) -> str:
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value.strip())
    return re.sub(r"[^A-Za-z0-9]+", "", words).lower()


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
