"""Build Linear issue title updates for research status changes.

The automation runner is expected to pass the incoming webhook payload to
``build_issue_title_update`` and apply the returned action if it is not ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalized_value(_status_name(context)) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(
        _first_present(context, ("id", "issueId", "issue_id", "identifier"))
    )
    title = _string_value(_first_present(context, ("title", "name")))

    if issue_id is None or title is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE_TEMPLATE.format(title=title),
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear/Cursor wrapper shapes into one lookup context."""

    context: dict[str, Any] = {}

    trigger_context = _mapping_value(event.get("triggerContext"))
    if trigger_context is not None:
        context.update(_issue_payload(trigger_context))
        context.update(trigger_context)

    data = _mapping_value(event.get("data"))
    if data is not None:
        context.update(_issue_payload(data))
        context.update(data)

    issue = _mapping_value(event.get("issue"))
    if issue is not None:
        context.update(issue)

    # Top-level event fields are the freshest in Cursor automation payloads.
    context.update(event)
    return context


def _issue_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    nested_issue = _mapping_value(payload.get("issue"))
    if nested_issue is not None:
        return dict(nested_issue)
    return dict(payload)


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        _normalized_event_name(context.get(key))
        for key in ("trigger", "webhookType", "action", "type")
    ]

    if any(name in {"statuschanged", "statuschange", "statusupdated"} for name in event_names):
        return True

    if any(name in {"issueupdated", "updatedissue", "update", "updated"} for name in event_names):
        updated_fields = _updated_fields(context)
        return not updated_fields or any(field in STATUS_FIELDS for field in updated_fields)

    return False


def _updated_fields(context: Mapping[str, Any]) -> set[str]:
    updated_fields = _first_present(
        context,
        (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
        ),
    )

    if isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, (list, tuple, set)):
        fields = updated_fields
    else:
        return set()

    return {_normalized_field_name(field) for field in fields if field is not None}


def _status_name(context: Mapping[str, Any]) -> Any:
    explicit_status = _first_present(
        context,
        ("newStatus", "new_status", "newState", "new_state", "newWorkflowState"),
    )
    if explicit_status is not None:
        return explicit_status

    state = _mapping_value(context.get("state"))
    if state is not None and state.get("name") is not None:
        return state["name"]

    workflow_state = _mapping_value(context.get("workflowState")) or _mapping_value(
        context.get("workflow_state")
    )
    if workflow_state is not None and workflow_state.get("name") is not None:
        return workflow_state["name"]

    status = context.get("status")
    if isinstance(status, Mapping):
        return status.get("name")
    return status


def _first_present(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in context and context[key] is not None:
            return context[key]
    return None


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalized_value(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel_case(text)).strip().lower()


def _normalized_event_name(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(text).lower())


def _normalized_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "", _split_camel_case(str(value)).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
