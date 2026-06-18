"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}

_DIRECT_STATUS_CHANGE_VALUES = {
    "statuschanged",
    "statuschange",
    "issuestatuschanged",
    "workflowstatechanged",
    "statechanged",
}

_UPDATE_VALUES = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation runtime passes slightly different payload shapes depending on
    the trigger source. This function accepts flat Cursor trigger contexts as
    well as nested Linear webhook-style issue update payloads.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not any(_normalize_status(status) == TARGET_STATUS for status in _status_candidates(event)):
        return None

    issue_id = _first_text(_issue_id_candidates(event))
    title = _first_text(_title_candidates(event))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_identifier(value)
        for value in _collect_key_values(event, {"trigger", "webhookType", "action", "type", "event", "eventType"})
    ]

    if any(
        value in _DIRECT_STATUS_CHANGE_VALUES
        or (("status" in value or "state" in value) and "chang" in value)
        for value in trigger_values
    ):
        return True

    if any(value in _UPDATE_VALUES or ("issue" in value and "update" in value) for value in trigger_values):
        return _has_status_update_marker(event)

    return False


def _has_status_update_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_identifier(key)

            if normalized_key in {"updatedfields", "changedfields"} and _contains_status_field(item):
                return True

            if normalized_key in {"changes", "changed", "updates", "updatedfrom"}:
                if isinstance(item, Mapping) and any(_is_status_field_name(field) for field in item):
                    return True
                if _has_status_update_marker(item):
                    return True

            if _has_status_update_marker(item):
                return True

    if isinstance(value, list):
        return any(_has_status_update_marker(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) or _contains_status_field(item) for key, item in value.items())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _status_candidates(event: Mapping[str, Any]) -> Iterable[str]:
    contexts = _payload_contexts(event)

    for context in contexts:
        for key in ("newStatus", "new_status", "newState", "new_state", "newWorkflowState", "toStatus", "toState"):
            yield _status_text(context.get(key))

    yield from _changed_status_candidates(event)

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            yield _status_text(context.get(key))


def _changed_status_candidates(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_identifier(key)

            if _is_status_field_name(key):
                yield from _new_change_values(item)
                continue

            if normalized_key in {"changes", "changed", "updates"} and isinstance(item, Mapping):
                for field, change in item.items():
                    if _is_status_field_name(field):
                        yield from _new_change_values(change)

            yield from _changed_status_candidates(item)

    elif isinstance(value, list):
        for item in value:
            yield from _changed_status_candidates(item)


def _new_change_values(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key in ("to", "toValue", "new", "newValue", "after", "name"):
            if key in value:
                yield _status_text(value.get(key))
        return

    yield _status_text(value)


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)

    for key in ("data", "issue", "payload"):
        child = event.get(key)
        add(child)
        if isinstance(child, Mapping):
            add(child.get("issue"))
            add(child.get("data"))

    return contexts


def _issue_id_candidates(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _payload_contexts(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            yield context.get(key)


def _title_candidates(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _payload_contexts(event):
        yield context.get("title")


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        if value is None:
            continue

        text = str(value).strip()
        if text:
            return text

    return None


def _status_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _status_text(value.get(key))
            if text:
                return text
        return ""

    return str(value).strip()


def _collect_key_values(value: Any, keys: set[str]) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in keys:
                yield item
            yield from _collect_key_values(item, keys)
    elif isinstance(value, list):
        for item in value:
            yield from _collect_key_values(item, keys)


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_identifier(value)
    return normalized in _STATUS_FIELD_NAMES or normalized.startswith("workflowstate")


def _normalize_status(value: Any) -> str:
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", str(value))
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words)
    return " ".join(words.casefold().split())


def _normalize_identifier(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "", str(value)).casefold()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().lstrip().startswith(PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
