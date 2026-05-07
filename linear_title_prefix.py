"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any, Iterator


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    locations = _event_locations(event)
    if not _is_status_change(locations):
        return None

    new_status = _first_field(
        locations,
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
    ) or _first_nested_field(locations, "state", "name")
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_locations = _issue_locations(event)
    issue_id = _first_field(issue_locations, "id", "issueId", "issue_id", "identifier")
    title = _first_field(issue_locations, "title")
    if not issue_id or not title:
        return None

    issue_id = str(issue_id).strip()
    title = str(title).strip()
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_locations(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    locations: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "payload", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            locations.append(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            locations.append(issue)

    payload = event.get("payload")
    if isinstance(payload, Mapping):
        issue = payload.get("issue")
        if isinstance(issue, Mapping):
            locations.append(issue)

    return locations


def _issue_locations(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    locations: list[Mapping[str, Any]] = []

    for key in ("triggerContext", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            locations.append(nested)

    for key in ("data", "payload"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            issue = nested.get("issue")
            if isinstance(issue, Mapping):
                locations.append(issue)
            locations.append(nested)

    locations.append(event)
    return locations


def _is_status_change(locations: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for value in _field_values(locations, "trigger", "action", "type")
    ]
    if any(value in {"status changed", "status change"} for value in trigger_values):
        return True

    if any(value in {"issue updated", "issue update", "updated"} for value in trigger_values):
        return _updated_fields_include_status(locations)

    if trigger_values:
        return False

    return _updated_fields_include_status(locations)


def _updated_fields_include_status(locations: list[Mapping[str, Any]]) -> bool:
    for value in _field_values(locations, "updatedFields", "updated_fields"):
        if isinstance(value, str):
            if _normalize_text(value) in {"status", "state"}:
                return True
            continue

        if isinstance(value, Mapping):
            if any(_normalize_text(key) in {"status", "state"} for key in value):
                return True
            continue

        try:
            iterator = iter(value)
        except TypeError:
            continue

        if any(_normalize_text(item) in {"status", "state"} for item in iterator):
            return True

    return False


def _first_field(locations: list[Mapping[str, Any]], *field_names: str) -> Any:
    return next(_field_values(locations, *field_names), None)


def _field_values(locations: list[Mapping[str, Any]], *field_names: str) -> Iterator[Any]:
    for location in locations:
        for field_name in field_names:
            value = location.get(field_name)
            if value is not None:
                return_value = value
                if isinstance(return_value, str):
                    return_value = return_value.strip()
                if return_value != "":
                    yield return_value


def _first_nested_field(
    locations: list[Mapping[str, Any]], field_name: str, nested_field_name: str
) -> Any:
    for location in locations:
        value = location.get(field_name)
        if isinstance(value, Mapping):
            nested_value = value.get(nested_field_name)
            if nested_value is not None and str(nested_value).strip():
                return nested_value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
