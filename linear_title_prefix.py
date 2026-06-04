"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELDS = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATE_EVENTS = {
    "issue update",
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_NEW_STATUS_KEYS = {
    "new status",
    "new state",
    "new workflow state",
    "to status",
    "to state",
    "to workflow state",
}
_CURRENT_STATUS_KEYS = {"status", "state", "workflow state"}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_PREFIX_RE = re.compile(
    rf"^\s*{re.escape(TITLE_PREFIX)}(?:\s*[:\-]\s*|\s+|$)",
    re.IGNORECASE,
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The Cursor automation payload has historically appeared in a few shapes:
    a flat ``triggerContext`` object, a nested Linear ``data.issue`` webhook,
    or a changes/updatedFields payload. This function accepts those shapes and
    returns ``None`` when no title change should be made.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _find_new_status(event)
    if _normalize_words(new_status) != _normalize_words(TARGET_STATUS):
        return None

    issue_id, title = _find_issue_fields(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Alias used by some automation runtimes."""

    return build_issue_title_update(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_tokens = {
        normalized
        for key in ("trigger", "event", "type", "action", "webhookType", "webhook_type")
        for normalized in _normalized_values_for_key(event, key)
    }

    if event_tokens & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_tokens & _ISSUE_UPDATE_EVENTS:
        return _updated_fields_include_status(event) or _changes_payload_includes_status(event)

    return _updated_fields_include_status(event) or _changes_payload_includes_status(event)


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_words(key) in _NEW_STATUS_KEYS:
                status = _extract_status_name(value)
                if status:
                    return status

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    for mapping in _preferred_issue_contexts(event):
        for key, value in mapping.items():
            if _normalize_words(key) in _CURRENT_STATUS_KEYS:
                status = _extract_status_name(value)
                if status:
                    return status

    return None


def _find_issue_fields(event: Mapping[str, Any]) -> tuple[str | None, str | None]:
    for mapping in _preferred_issue_contexts(event):
        issue_id = _direct_text_value(mapping, _ISSUE_ID_KEYS)
        title = _direct_text_value(mapping, ("title",))
        if issue_id and title:
            return issue_id, title

    for mapping in _walk_mappings(event):
        issue_id = _direct_text_value(mapping, _ISSUE_ID_KEYS)
        title = _direct_text_value(mapping, ("title",))
        if issue_id and title:
            return issue_id, title

    return None, None


def _preferred_issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
    ):
        value: Any = event
        for segment in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(segment)
        if isinstance(value, Mapping):
            contexts.append(value)
    return contexts


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_words(key)
            if normalized_key in _STATUS_FIELDS:
                status = _extract_changed_to_value(nested)
                if status:
                    return status
            if normalized_key in {"changes", "updated fields", "field updates"}:
                status = _status_from_changes(nested)
                if status:
                    return status
            elif isinstance(nested, (Mapping, list, tuple)):
                status = _status_from_changes(nested)
                if status:
                    return status
    elif _is_non_string_sequence(value):
        for item in value:
            status = _status_from_changes(item)
            if status:
                return status
    return None


def _extract_changed_to_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "value", "name"):
            if key in value:
                status = _extract_status_name(value[key])
                if status:
                    return status
    return _extract_status_name(value)


def _extract_status_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "status", "state", "title"):
            if key in value:
                status = _extract_status_name(value[key])
                if status:
                    return status
    return None


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_words(key)
            if normalized_key in {"updated fields", "changed fields"}:
                if _field_list_contains_status(nested):
                    return True
            if _updated_fields_include_status(nested):
                return True
    elif _is_non_string_sequence(value):
        return any(_updated_fields_include_status(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_words(key)
            if normalized_key in {"changes", "field updates"}:
                return _changes_include_status(nested)
            if normalized_key in _STATUS_FIELDS:
                return True
            if _changes_include_status(nested):
                return True
    elif _is_non_string_sequence(value):
        return any(_changes_include_status(item) for item in value)
    return False


def _changes_payload_includes_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_words(key)
            if normalized_key in {"changes", "field updates"}:
                if _changes_include_status(nested):
                    return True
            elif _changes_payload_includes_status(nested):
                return True
    elif _is_non_string_sequence(value):
        return any(_changes_payload_includes_status(item) for item in value)
    return False


def _field_list_contains_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in _STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(
            _normalize_words(key) in _STATUS_FIELDS
            or _field_list_contains_status(nested)
            for key, nested in value.items()
        )
    if _is_non_string_sequence(value):
        return any(_field_list_contains_status(item) for item in value)
    return False


def _normalized_values_for_key(value: Any, wanted_key: str) -> Iterable[str]:
    wanted = _normalize_words(wanted_key)
    for mapping in _walk_mappings(value):
        for key, nested in mapping.items():
            if _normalize_words(key) == wanted and isinstance(nested, str):
                yield _normalize_words(nested)


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif _is_non_string_sequence(value):
        for item in value:
            yield from _walk_mappings(item)


def _direct_text_value(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return bool(_TITLE_PREFIX_RE.match(title))


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a Linear issue-title update for research status changes."
    )
    parser.add_argument(
        "payload",
        nargs="?",
        help="Path to a JSON payload file. Reads stdin when omitted.",
    )
    args = parser.parse_args(argv)

    raw_payload = open(args.payload, encoding="utf-8").read() if args.payload else sys.stdin.read()
    event = json.loads(raw_payload)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
