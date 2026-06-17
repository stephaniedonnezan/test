"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
    "workflowstatus",
    "workflowstatusid",
    "workflowstatusname",
}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatuschanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_TRIGGER_KEYS = {
    "action",
    "event",
    "eventtype",
    "trigger",
    "type",
    "webhooktype",
}
_UPDATED_FIELD_KEYS = {
    "changedfields",
    "changedproperties",
    "updatedfields",
    "updatedproperties",
}
_CHANGE_CONTAINER_KEYS = {
    "changes",
    "changed",
    "diff",
    "previousvalues",
    "updatedfrom",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStatus",
    "new_workflow_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
    "workflowStatusName",
    "workflow_status_name",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "toWorkflowState",
    "to_workflow_state",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(TITLE_PREFIX)}(?:\s*[-:]\s*|\s+|$)",
    flags=re.IGNORECASE,
)


def update_issue_title_for_status(
    title: str,
    new_status: str,
    prefix: str = TITLE_PREFIX,
) -> str:
    """Return ``title`` prefixed when ``new_status`` is the research status."""

    if _normalize_words(new_status) != TARGET_STATUS:
        return title
    return _prefix_title(title, prefix)


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Return the updated title for a status-change payload, if one is needed."""

    if not isinstance(payload, Mapping):
        return None
    if not _is_status_change_event(payload):
        return None

    new_status = _extract_new_status(payload)
    title = _extract_title(payload)
    if not title or _normalize_words(new_status) != TARGET_STATUS:
        return None

    updated_title = _prefix_title(title)
    if updated_title == title:
        return None
    return updated_title


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None
    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    updated_title = _prefix_title(title)
    if updated_title == title:
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": updated_title,
    }


def _prefix_title(title: str, prefix: str = TITLE_PREFIX) -> str:
    """Add the research marker while preserving already-prefixed titles."""

    if _PREFIX_PATTERN.match(title):
        return title

    clean_title = title.strip()
    if not clean_title:
        return prefix
    return f"{prefix}: {clean_title}"


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_tokens = {
        _normalize_token(value)
        for mapping in _iter_mappings(event)
        for key, value in mapping.items()
        if _normalize_token(key) in _TRIGGER_KEYS
    }

    if trigger_tokens & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True
    if trigger_tokens & _GENERIC_UPDATE_TRIGGERS:
        return _status_field_changed(event)
    return False


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        for key, value in mapping.items():
            normalized_key = _normalize_token(key)
            if normalized_key in _UPDATED_FIELD_KEYS and _mentions_status_field(value):
                return True
            if normalized_key in _CHANGE_CONTAINER_KEYS and _change_mentions_status(value):
                return True
    return False


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(
            _is_status_field_name(key) or _mentions_status_field(nested_value)
            for key, nested_value in value.items()
        )
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_mentions_status_field(item) for item in value)
    return False


def _change_mentions_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_is_status_field_name(field) for field in value)


def _is_status_field_name(value: Any) -> bool:
    return _normalize_token(value) in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key in _EXPLICIT_STATUS_KEYS:
            if key in mapping:
                status = _status_name(mapping[key])
                if status:
                    return status

    for mapping in _iter_mappings(event):
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            status = _status_from_changes(changes)
            if status:
                return status

    for mapping in _candidate_mappings(event):
        for key in _CURRENT_STATUS_KEYS:
            if key in mapping:
                status = _status_name(mapping[key])
                if status:
                    return status

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for field, value in changes.items():
        if not _is_status_field_name(field):
            continue

        if isinstance(value, Mapping):
            for key in ("to", "new", "newValue", "new_value", "after", "current", "value", "name"):
                if key in value:
                    status = _status_name(value[key])
                    if status:
                        return status
        else:
            status = _status_name(value)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                status = _status_name(value[key])
                if status:
                    return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_text(event, _ISSUE_ID_KEYS)


def _extract_title(event: Mapping[str, Any]) -> str | None:
    return _first_text(event, _TITLE_KEYS)


def _first_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key in keys:
            if key in mapping:
                text = _text_value(mapping[key])
                if text:
                    return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            if key in value:
                text = _text_value(value[key])
                if text:
                    return text
    return None


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)
        _append_mapping(candidates, trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(candidates, data.get("issue"))
        _append_mapping(candidates, data.get("data"))
        candidates.append(data)

    _append_mapping(candidates, event.get("issue"))
    candidates.append(event)
    return candidates


def _append_mapping(candidates: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping):
        candidates.append(value)


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_mappings(child)


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_token(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _load_payload(input_path: str | None) -> Mapping[str, Any]:
    if input_path:
        with open(input_path, encoding="utf-8") as input_file:
            payload = json.load(input_file)
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise ValueError("Input payload must be a JSON object.")
    return payload


def main(argv: list[str] | None = None) -> int:
    """Read a JSON event and print the requested title update action."""

    parser = argparse.ArgumentParser(
        description="Prefix Linear issue titles when status changes to to research."
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON payload. Reads stdin when omitted.",
    )
    args = parser.parse_args(argv)

    event = _load_payload(args.input)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
