"""Build Linear issue title updates for the research status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _collect_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one payload."""

    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        for nested_key in ("issue", "data", "triggerContext"):
            nested = value.get(nested_key)
            if isinstance(nested, Mapping):
                merge(nested)
        payload.update(value)

    merge(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_markers = [
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]

    if any(marker in {"status changed", "status change", "status updated"} for marker in event_markers):
        return True

    if any(marker in {"issue updated", "updated issue", "update", "updated"} for marker in event_markers):
        return _has_changed_status_field(payload)

    return False


def _has_changed_status_field(payload: Mapping[str, Any]) -> bool:
    changed_fields = payload.get("updatedFields") or payload.get("changedFields")
    if _field_list_mentions_status(changed_fields):
        return True

    updated_from = payload.get("updatedFrom") or payload.get("previousValues")
    if isinstance(updated_from, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in updated_from)

    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        values: list[Any] = [value]
    elif isinstance(value, list | tuple | set):
        values = list(value)
    else:
        return False

    return any(_normalize_key(field) in _STATUS_FIELD_NAMES for field in values)


def _new_status(payload: Mapping[str, Any]) -> str | None:
    explicit_status = _first_text(
        payload,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit_status:
        return explicit_status

    for key in ("status", "state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name:
                return name
        elif isinstance(value, str):
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, int | float):
            return str(value)
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    words = _split_words(value)
    if not words:
        return None
    return " ".join(words)


def _normalize_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    words = _split_words(value)
    if not words:
        return None
    return "".join(words)


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.findall(r"[a-z0-9]+", spaced.lower())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
