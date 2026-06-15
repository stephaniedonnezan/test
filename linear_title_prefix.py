"""Build Linear issue-title updates for issues moving to To Research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}
_DIRECT_STATUS_CHANGE_TYPES = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_UPDATE_TYPES = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The returned dictionary is intentionally small so an outer automation can
    translate it into the appropriate Linear API call.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _text_from_keys(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _text_from_keys(contexts, ("title",))
    if not issue_id or not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue dictionaries in useful priority order."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    add(event.get("data"))
    add(_mapping_value(event.get("data"), "issue"))
    add(event.get("issue"))

    for context in list(contexts):
        add(context.get("triggerContext"))
        add(context.get("data"))
        add(context.get("issue"))

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_types = _event_type_tokens(contexts)
    if any(event_type in _DIRECT_STATUS_CHANGE_TYPES for event_type in event_types):
        return True

    if any(event_type in _UPDATE_TYPES for event_type in event_types):
        return _has_status_field_change(contexts)

    return False


def _event_type_tokens(contexts: Sequence[Mapping[str, Any]]) -> list[str]:
    tokens: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                tokens.append(_normalize_token(value))
    return tokens


def _has_status_field_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if any(_is_status_field(field) for field in _field_names(context.get(key))):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
            if any(_is_status_change_entry(entry) for entry in changes):
                return True

    return False


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> Any:
    for context in contexts:
        value = _first_present(
            context,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if value is not None:
            return value

    for context in contexts:
        value = _status_from_changes(context.get("changes"))
        if value is not None:
            return value

    for context in contexts:
        value = _first_present(context, ("status", "state", "workflowState", "workflow_state"))
        if value is not None:
            return value

    return None


def _status_from_changes(changes: Any) -> Any:
    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if not _is_status_field(field):
                continue
            if isinstance(value, Mapping):
                changed_value = _first_present(
                    value,
                    ("to", "toStatus", "new", "newValue", "after", "name"),
                )
                if changed_value is not None:
                    return changed_value
            return value

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for entry in changes:
            if not _is_status_change_entry(entry) or not isinstance(entry, Mapping):
                continue
            value = _first_present(entry, ("to", "toStatus", "new", "newValue", "after", "value"))
            if value is not None:
                return value

    return None


def _is_status_change_entry(entry: Any) -> bool:
    if not isinstance(entry, Mapping):
        return False
    field = _first_present(entry, ("field", "name", "key"))
    return _is_status_field(field)


def _field_names(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        return value.keys()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        fields: list[Any] = []
        for item in value:
            if isinstance(item, Mapping):
                fields.append(_first_present(item, ("field", "name", "key")))
            else:
                fields.append(item)
        return fields
    return ()


def _text_from_keys(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            text = _text(value)
            if text:
                return text
    return None


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return None


def _is_status_field(value: Any) -> bool:
    return _normalize_token(value) in _STATUS_FIELDS


def _normalize_status(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return _words(text)


def _normalize_token(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", _words(text))


def _words(value: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _first_present(
            value,
            ("name", "title", "label", "value", "newValue", "to", "after"),
        )
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _has_title_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
