"""Build Linear issue title updates for issues moved to To Research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    status = _first_text(
        payload,
        ("newStatus", "new_status", "status", "state", "workflowState"),
        nested=(("status", "name"), ("state", "name"), ("workflowState", "name")),
    )
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title",))
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook and automation nesting shapes into one map."""
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_payload(value))

    # Outer values win because automation metadata can sit next to issue data.
    payload.update(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    triggers = _normalized_trigger_values(payload)
    if any(
        trigger in {"statuschanged", "statuschange", "statusupdated"}
        for trigger in triggers
    ):
        return True

    if any(trigger in {"issueupdated", "updatedissue"} for trigger in triggers):
        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        return _contains_status_field(updated_fields)

    return False


def _normalized_trigger_values(payload: Mapping[str, Any]) -> list[str]:
    values = (
        payload.get("trigger"),
        payload.get("action"),
        payload.get("type"),
        payload.get("webhookType"),
    )
    return [
        normalized
        for value in values
        if isinstance(value, str)
        for normalized in (_normalize_token(value),)
        if normalized is not None
    ]


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in {"status", "state", "workflowstate"}

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_text(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    nested: tuple[tuple[str, str], ...] = (),
) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value

    for parent_key, child_key in nested:
        parent = payload.get(parent_key)
        if isinstance(parent, Mapping):
            value = parent.get(child_key)
            if isinstance(value, str):
                return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_token(value: str | None) -> str | None:
    status = _normalize_status(value)
    if status is None:
        return None
    return status.replace(" ", "")


def main() -> int:
    """Read a Linear event JSON object from stdin and print the update action."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, separators=(",", ":")))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
