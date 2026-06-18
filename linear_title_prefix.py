"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b", re.IGNORECASE)
_CAMEL_CASE_BOUNDARY_RE = re.compile(r"([a-z0-9])([A-Z])")
_NON_WORD_RE = re.compile(r"[^A-Za-z0-9]+")

_EVENT_KEYS = ("trigger", "event", "action", "type", "webhookType", "webhook_type")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title", "name", "summary")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for status changes to research.

    The automation runner can pass either a flat Cursor ``triggerContext`` payload
    or a nested Linear webhook payload. Non-status events, status changes to other
    states, missing issue details, and already-prefixed titles are ignored.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if not _is_target_status(_extract_new_status(contexts)):
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _PREFIX_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects, preferring outer trigger data."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        yield value

        for key in ("triggerContext", "trigger_context", "data", "issue", "node"):
            child = value.get(key)
            if isinstance(child, Mapping):
                yield from visit(child)

    yield from visit(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if _has_direct_status_change_event(contexts):
        return True

    return _has_status_change_details(contexts)


def _has_direct_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _EVENT_KEYS:
            event_name = _normalized_words(context.get(key))
            if not event_name:
                continue
            if event_name in {
                "status changed",
                "status change",
                "status updated",
                "issue status changed",
                "issue status updated",
                "workflow state changed",
                "workflow state updated",
            }:
                return True
            if "status" in event_name and (
                "change" in event_name or "changed" in event_name or "update" in event_name or "updated" in event_name
            ):
                return True
            if "workflow state" in event_name and ("change" in event_name or "update" in event_name):
                return True

    return False


def _has_status_change_details(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        if _updated_fields_include_status(context.get("updatedFields")):
            return True
        if _updated_fields_include_status(context.get("updated_fields")):
            return True
        if _mapping_keys_include_status(context.get("changes")):
            return True
        if _mapping_keys_include_status(context.get("updatedFrom")):
            return True
        if _mapping_keys_include_status(context.get("updated_from")):
            return True

    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        fields = re.split(r"[,;\s]+", value)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        fields = value
    else:
        return False

    return any(_is_status_field(field) for field in fields)


def _mapping_keys_include_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    return any(_is_status_field(key) for key in value.keys())


def _is_status_field(value: Any) -> bool:
    normalized = _normalized_words(value)
    return bool(normalized and normalized in _STATUS_FIELD_NAMES)


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_text(contexts, _NEW_STATUS_KEYS)
    if explicit:
        return explicit

    changed_value = _status_from_change_details(contexts)
    if changed_value:
        return changed_value

    return _first_status_text(contexts)


def _status_from_change_details(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "updated", "updatedFields", "updated_fields"):
            value = context.get(key)
            status = _status_from_change_mapping(value)
            if status:
                return status

    return None


def _status_from_change_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if not _is_status_field(key):
            continue
        if isinstance(change, Mapping):
            for value_key in ("new", "to", "newValue", "new_value", "after", "value", "name"):
                status = _coerce_text(change.get(value_key))
                if status:
                    return status
        else:
            status = _coerce_text(change)
            if status:
                return status

    return None


def _first_status_text(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _STATUS_KEYS:
            value = context.get(key)
            if isinstance(value, Mapping):
                status = _first_text([value], ("name", "title", "label"))
                if status:
                    return status
            else:
                status = _coerce_text(value)
                if status:
                    return status

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _coerce_text(context.get(key))
            if value:
                return value

    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_target_status(value: Any) -> bool:
    return _normalized_words(value) == TARGET_STATUS


def _normalized_words(value: Any) -> str | None:
    text = _coerce_text(value)
    if not text:
        return None

    text = _CAMEL_CASE_BOUNDARY_RE.sub(r"\1 \2", text)
    text = _NON_WORD_RE.sub(" ", text)
    return " ".join(text.lower().split()) or None


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
