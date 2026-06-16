"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = {"trigger", "webhooktype", "event", "type", "action"}
_EXPLICIT_STATUS_KEYS = {"newstatus", "newstate", "newworkflowstate"}
_CURRENT_STATUS_KEYS = {"status", "state", "workflowstate"}
_STATUS_FIELD_KEYS = {"status", "state", "workflowstate"}
_UPDATED_FIELD_KEYS = {
    "updatedfields",
    "changedfields",
    "changed",
    "changes",
    "updatedproperties",
}
_CHANGE_NEW_VALUE_KEYS = {
    "to",
    "after",
    "new",
    "current",
    "newvalue",
    "tovalue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters to-research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if issue_id is None or title is None:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for mapping in _candidate_mappings(event)
        for key, value in mapping.items()
        if _normalize_key(key) in _TRIGGER_KEYS
    ]

    if any(_looks_like_status_change(value) for value in trigger_values):
        return True

    if any(_looks_like_update(value) for value in trigger_values):
        return _has_status_field_change(event)

    return _has_status_field_change(event) and _extract_new_status(event) is not None


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for key_set in (_EXPLICIT_STATUS_KEYS,):
        for mapping in _candidate_mappings(event):
            for key, value in mapping.items():
                if _normalize_key(key) in key_set:
                    status = _status_value(value)
                    if status is not None:
                        return status

    changed_status = _extract_changed_status(event)
    if changed_status is not None:
        return changed_status

    for mapping in _candidate_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) in _CURRENT_STATUS_KEYS:
                status = _status_value(value)
                if status is not None:
                    return status

    return None


def _extract_changed_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) not in {"changes", "changed"}:
                continue

            if isinstance(value, Mapping):
                status = _extract_status_from_change_map(value)
                if status is not None:
                    return status

            if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                for item in value:
                    if not isinstance(item, Mapping):
                        continue

                    field = _string_value(
                        item.get("field")
                        or item.get("name")
                        or item.get("key")
                        or item.get("property")
                    )
                    if field is None or not _is_status_field(field):
                        continue

                    for value_key, changed_value in item.items():
                        if _normalize_key(value_key) in _CHANGE_NEW_VALUE_KEYS:
                            status = _status_value(changed_value)
                            if status is not None:
                                return status

    return None


def _extract_status_from_change_map(changes: Mapping[str, Any]) -> str | None:
    for field, change in changes.items():
        if not _is_status_field(str(field)):
            continue

        status = _status_value(change)
        if status is not None:
            return status

        if not isinstance(change, Mapping):
            continue

        for key, value in change.items():
            if _normalize_key(key) in _CHANGE_NEW_VALUE_KEYS:
                status = _status_value(value)
                if status is not None:
                    return status

    return None


def _has_status_field_change(event: Mapping[str, Any]) -> bool:
    for mapping in _candidate_mappings(event):
        for key, value in mapping.items():
            normalized_key = _normalize_key(key)
            if normalized_key in _UPDATED_FIELD_KEYS:
                if _contains_status_field(value):
                    return True

            if normalized_key in {"changes", "changed"}:
                if isinstance(value, Mapping) and any(
                    _is_status_field(str(field)) for field in value.keys()
                ):
                    return True
                if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                    for item in value:
                        if isinstance(item, Mapping) and _contains_status_field(
                            item.get("field")
                            or item.get("name")
                            or item.get("key")
                            or item.get("property")
                        ):
                            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(str(key)) for key in value.keys())

    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for id_key in ("issueid", "identifier", "key", "id"):
        for mapping in _candidate_mappings(event):
            for key, value in mapping.items():
                if _normalize_key(key) != id_key:
                    continue

                issue_id = _string_value(value)
                if issue_id is not None:
                    return issue_id

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) != "title":
                continue

            title = _string_value(value)
            if title is not None:
                return title

    return None


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/trigger mappings first, then all nested mappings."""

    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            candidates.append(value)

    add(event.get("triggerContext"))
    add(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))

    for mapping in _walk_mappings(event):
        add(mapping)

    return candidates


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for child in value:
            yield from _walk_mappings(child)


def _status_value(value: Any) -> str | None:
    direct = _string_value(value)
    if direct is not None:
        return direct

    if not isinstance(value, Mapping):
        return None

    for key in ("name", "title", "label"):
        if key in value:
            status = _string_value(value[key])
            if status is not None:
                return status

    return None


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _looks_like_status_change(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"status changed", "state changed", "workflow state changed"}


def _looks_like_update(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"update", "updated", "issue updated", "updated issue"}


def _is_status_field(value: str) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_KEYS


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
