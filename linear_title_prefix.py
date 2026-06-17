"""Build Linear issue title update actions for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state", "stateid", "statusid"}
_TRIGGER_KEYS = {"trigger", "webhooktype", "trigger_type", "triggertype", "action", "type", "event"}
_NEW_STATUS_KEYS = {
    "newstatus",
    "new_status",
    "tostatus",
    "to_status",
    "statusname",
    "status_name",
    "statename",
    "state_name",
    "workflowstatename",
    "workflow_state_name",
}
_TITLE_KEYS = ("title", "name")
_IDENTIFIER_KEYS = ("identifier", "key", "issueId", "issue_id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The function accepts the flat ``triggerContext`` payload Cursor automations
    provide and common nested Linear webhook shapes. It is side-effect free so
    callers can decide how to execute the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_mappings(event))
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_value(new_status) != TARGET_STATUS:
        return None

    issue = _extract_issue(event)
    title = _extract_title(issue, candidates)
    issue_id = _extract_issue_id(issue, candidates)
    if not title or not issue_id:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title.strip()}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield mappings from most-specific automation metadata through nested data."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping):
            object_id = id(value)
            if object_id in seen:
                return
            seen.add(object_id)
            yield value
            for child in value.values():
                yield from visit(child)
        elif isinstance(value, list):
            for child in value:
                yield from visit(child)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data

    yield from visit(event)


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    direct_status_trigger = False
    generic_issue_update = False
    changed_status_field = False

    for candidate in candidates:
        for key, value in candidate.items():
            normalized_key = _normalize_key(key)
            if normalized_key in _TRIGGER_KEYS:
                normalized_value = _normalize_value(value)
                if "status changed" in normalized_value or "state changed" in normalized_value:
                    direct_status_trigger = True
                if normalized_value in {"update", "updated", "issue updated", "updated issue"}:
                    generic_issue_update = True
            elif normalized_key in {"updatedfields", "updated_fields", "changedfields", "changed_fields"}:
                changed_status_field = changed_status_field or _contains_status_field(value)
            elif normalized_key in {"changes", "updatedfrom", "updated_from"}:
                changed_status_field = changed_status_field or _contains_status_change(value)

    return direct_status_trigger or (generic_issue_update and changed_status_field)


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> Any:
    fallback: Any = None

    for candidate in candidates:
        for key, value in candidate.items():
            normalized_key = _normalize_key(key)
            if normalized_key in _NEW_STATUS_KEYS:
                return value
            if normalized_key in {"changes", "updatedfrom", "updated_from"}:
                changed_value = _extract_status_from_change(value)
                if changed_value is not None:
                    return changed_value
            if normalized_key in {"status", "state", "workflowstate", "workflow_state"} and fallback is None:
                fallback = _extract_named_value(value)

    return fallback


def _extract_status_from_change(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return None

    for key, changed_value in value.items():
        if _normalize_key(key) not in _STATUS_FIELDS:
            continue
        if isinstance(changed_value, Mapping):
            for new_key in ("newValue", "new_value", "to", "after", "name"):
                if new_key in changed_value:
                    return changed_value[new_key]
        return changed_value

    return None


def _extract_issue(event: Mapping[str, Any]) -> Mapping[str, Any]:
    for path in (("data", "issue"), ("issue",), ("triggerContext",)):
        value: Any = event
        for part in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(part)
        if isinstance(value, Mapping):
            return value
    return event


def _extract_title(issue: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]]) -> str | None:
    for source in (issue, *candidates):
        for key in _TITLE_KEYS:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_issue_id(issue: Mapping[str, Any], candidates: Iterable[Mapping[str, Any]]) -> str | None:
    for source in (issue, *candidates):
        for key in _IDENTIFIER_KEYS:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for source in (issue, *candidates):
        value = source.get("id")
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELDS
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELDS for key in value)
    return False


def _contains_status_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELDS for key in value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_change(item) for item in value)
    return False


def _extract_named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "label"):
            if key in value:
                return value[key]
    return value


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", _split_camel(str(value)).lower())


def _normalize_value(value: Any) -> str:
    named_value = _extract_named_value(value)
    text = _split_camel(str(named_value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
