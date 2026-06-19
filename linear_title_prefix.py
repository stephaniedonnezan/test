"""Build Linear issue title update actions for research status transitions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_TITLE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = frozenset(
    {
        "status",
        "statusid",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
    }
)
_STATUS_CHANGE_EVENT_NAMES = frozenset(
    {
        "statuschange",
        "statuschanged",
        "statusupdate",
        "statusupdated",
        "statechange",
        "statechanged",
        "workflowstatechange",
        "workflowstatechanged",
    }
)
_UPDATE_EVENT_NAMES = frozenset(
    {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
)
_COMMON_WRAPPER_KEYS = ("triggerContext", "data", "issue")
_TITLE_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(TITLE_PREFIX)}(?:\b|\s*[-:]\s*)",
    flags=re.IGNORECASE,
)


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_title_prefix(clean_title):
        return None

    return {
        "action": UPDATE_TITLE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect flat automation data and common nested Linear payload wrappers."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def collect(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)

        contexts.append(value)
        for key in _COMMON_WRAPPER_KEYS:
            collect(value.get(key))

    collect(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_update_event = False

    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            event_name = _normalize_token(context.get(key))
            if event_name in _STATUS_CHANGE_EVENT_NAMES:
                return True
            if event_name in _UPDATE_EVENT_NAMES:
                saw_update_event = True

    return saw_update_event and _changed_fields_include_status(contexts)


def _changed_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_mentions_status(context.get(key)):
                return True

        for key in ("updatedFrom", "updated_from", "previousValues", "previous_values"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_field_name_mentions_status(field) for field in value):
                return True

        for key in ("changes", "changed", "updates"):
            if _changes_mention_status(context.get(key)):
                return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_mentions_status(value)
    if isinstance(value, Mapping):
        return any(_field_name_mentions_status(key) for key in value)
    if isinstance(value, Iterable):
        return any(_field_name_mentions_status(item) for item in value)
    return False


def _changes_mention_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_field_name_mentions_status(key) for key in value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_change_mentions_status(change) for change in value)
    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, Mapping):
        return _field_name_mentions_status(
            _first_mapping_value(change, ("field", "name", "key", "property"))
        )
    return _field_name_mentions_status(change)


def _field_name_mentions_status(value: Any) -> bool:
    return _normalize_token(value) in _STATUS_FIELD_NAMES


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    direct_status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if direct_status:
        return direct_status

    for context in contexts:
        for key in ("changes", "changed", "updates"):
            status = _status_from_changes(context.get(key))
            if status:
                return status

        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_text(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if not _field_name_mentions_status(field):
                continue

            status = _status_text(value)
            if status:
                return status

    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping) or not _change_mentions_status(change):
                continue

            status = _status_text(
                _first_mapping_value(change, ("newValue", "new_value", "to", "after", "value"))
            )
            if status:
                return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(
            (value,),
            ("name", "title", "label", "newValue", "new_value", "to", "after", "value"),
        )
    return _text_value(value)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        value = _first_mapping_value(context, keys)
        text = _text_value(value)
        if text:
            return text
    return None


def _first_mapping_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    if isinstance(value, int):
        return str(value)
    return None


def _has_title_prefix(title: str) -> bool:
    return bool(_TITLE_PREFIX_PATTERN.match(title))


def _normalize_words(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return " ".join(re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).split())


def _normalize_token(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _load_event(input_path: str | None) -> Mapping[str, Any]:
    if input_path:
        with open(input_path, encoding="utf-8") as input_file:
            event = json.load(input_file)
    else:
        event = json.load(sys.stdin)

    if not isinstance(event, Mapping):
        raise ValueError("Input payload must be a JSON object.")
    return event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a Linear issue-title update when status changes to to research."
    )
    parser.add_argument(
        "--input",
        help="Path to a JSON event payload. Reads stdin when omitted.",
    )
    args = parser.parse_args(argv)

    action = build_issue_title_update(_load_event(args.input))
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
