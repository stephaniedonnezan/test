"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    root = event
    trigger_context = _mapping(root.get("triggerContext"))
    data = _mapping(root.get("data"))
    issue = _mapping(root.get("issue")) or _mapping(data.get("issue"))

    metadata_contexts = [trigger_context, root, data]
    issue_contexts = [trigger_context, issue, data, root]

    if not _is_status_change_event(metadata_contexts, data):
        return None

    if _normalize_status(_extract_new_status(metadata_contexts, issue)) != TARGET_STATUS:
        return None

    issue_id = _first_text(issue_contexts, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(issue_contexts, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(
    metadata_contexts: list[Mapping[str, Any]], data: Mapping[str, Any]
) -> bool:
    event_tokens = [
        _normalize_token(str(value))
        for context in metadata_contexts
        for key in ("trigger", "webhookType", "eventType", "type", "action")
        if (value := context.get(key)) is not None
    ]

    if any(token in {"statuschanged", "statuschange"} for token in event_tokens):
        return True

    if any(token in {"update", "updated", "issueupdated", "updatedissue"} for token in event_tokens):
        return _updated_fields_include_status(data)

    return False


def _updated_fields_include_status(data: Mapping[str, Any]) -> bool:
    updated_fields = data.get("updatedFields")
    if isinstance(updated_fields, list):
        for field in updated_fields:
            if _normalize_field_name(str(field)) in STATUS_FIELD_NAMES:
                return True

    updated_from = data.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        for field in updated_from:
            if _normalize_field_name(str(field)) in STATUS_FIELD_NAMES:
                return True

    return False


def _extract_new_status(
    metadata_contexts: list[Mapping[str, Any]], issue: Mapping[str, Any]
) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
        "status",
    )

    direct_status = _first_text(metadata_contexts, explicit_status_keys)
    if direct_status:
        return direct_status

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = issue.get(key)
        if isinstance(value, Mapping):
            status_name = _text(value.get("name"))
            if status_name:
                return status_name
        else:
            status_name = _text(value)
            if status_name:
                return status_name

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text(context.get(key))
            if value:
                return value
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _normalize_status(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", _split_camel_case(value).replace("_", " ").replace("-", " ")).strip().casefold()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).casefold())


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", _split_camel_case(value).replace(".", "_").casefold())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read a JSON event from stdin and print the generated action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
