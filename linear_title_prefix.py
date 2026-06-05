"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
_NEW_STATUS_FIELD_NAMES = {
    "newstatus",
    "newstate",
    "newworkflowstate",
    "newworkflowstatus",
    "targetstatus",
    "targetstate",
    "tostatus",
    "tostate",
}
_TITLE_PREFIX_RE = re.compile(rf"^\s*{re.escape(PREFIX)}\b", re.IGNORECASE)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    mappings = list(_walk_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    if not any(_normalize_text(status) == TARGET_STATUS for status in _new_status_candidates(mappings)):
        return None

    issue_id = _first_text(mappings, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(mappings, ("title", "name"))
    if not issue_id or not title or _TITLE_PREFIX_RE.match(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for status-change automation handlers."""

    return build_issue_title_update(event)


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for mapping in mappings:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            value = mapping.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_text(value))

    has_explicit_status_change = any(
        value in {"status changed", "state changed", "workflow state changed"}
        or value.endswith(" status changed")
        or value.endswith(" state changed")
        for value in trigger_values
    )
    if has_explicit_status_change:
        return True

    is_issue_update = any(
        value
        in {
            "issue updated",
            "updated issue",
            "issue update",
            "update",
            "updated",
        }
        for value in trigger_values
    )
    return is_issue_update and _has_status_change_evidence(mappings)


def _has_status_change_evidence(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        if _updated_fields_include_status(mapping.get("updatedFields")):
            return True
        if _change_mapping_includes_status(mapping.get("changes")):
            return True
        if _change_mapping_includes_status(mapping.get("updatedFrom")):
            return True
    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _compact(value) in _STATUS_FIELD_NAMES
    if isinstance(value, list):
        return any(_updated_fields_include_status(item) for item in value)
    if isinstance(value, Mapping):
        return any(_compact(key) in _STATUS_FIELD_NAMES for key in value)
    return False


def _change_mapping_includes_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _compact(key) in _STATUS_FIELD_NAMES or _change_mapping_includes_status(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_change_mapping_includes_status(item) for item in value)
    return False


def _new_status_candidates(mappings: list[Mapping[str, Any]]) -> list[str]:
    candidates: list[str] = []

    for mapping in mappings:
        for key, value in mapping.items():
            compact_key = _compact(key)
            if compact_key in _NEW_STATUS_FIELD_NAMES:
                candidates.extend(_extract_text_values(value))

    for mapping in mappings:
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            candidates.extend(_status_values_from_change_mapping(changes))

    for mapping in mappings:
        for key, value in mapping.items():
            compact_key = _compact(key)
            if compact_key in _STATUS_FIELD_NAMES:
                candidates.extend(_extract_current_status_values(value))

    return candidates


def _status_values_from_change_mapping(changes: Mapping[str, Any]) -> list[str]:
    candidates: list[str] = []
    for key, value in changes.items():
        if _compact(key) in _STATUS_FIELD_NAMES:
            if isinstance(value, Mapping):
                for target_key in ("to", "after", "new", "current", "name"):
                    candidates.extend(_extract_text_values(value.get(target_key)))
            else:
                candidates.extend(_extract_text_values(value))
        elif isinstance(value, Mapping):
            candidates.extend(_status_values_from_change_mapping(value))
    return candidates


def _extract_current_status_values(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        for key in ("name", "status", "state", "workflowState"):
            extracted = _extract_text_values(value.get(key))
            if extracted:
                return extracted
        return []
    return _extract_text_values(value)


def _extract_text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status"):
            extracted = _extract_text_values(value.get(key))
            if extracted:
                return extracted
    return []


def _first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    compact_keys = {_compact(key) for key in keys}
    for mapping in mappings:
        for key, value in mapping.items():
            if _compact(key) in compact_keys:
                values = _extract_text_values(value)
                if values:
                    return values[0]
    return None


def _compact(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _normalize_text(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[^a-zA-Z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
