"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payloads = _payload_layers(event)
    if not _is_status_change_event(payloads):
        return None

    status = _first_text(payloads, ("newStatus", "new_status"))
    if status is None:
        status = _first_text(payloads, ("status",))
    if status is None:
        status = _first_nested_text(payloads, ("state", "workflowState", "status"), "name")
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payloads, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payloads, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _payload_layers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload maps from broadest metadata to nested issue details."""
    layers: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        if value not in layers:
            layers.append(value)
        for key in ("triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return layers


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    event_markers = _all_text(payloads, ("trigger", "webhookType", "action", "type"))
    normalized_markers = {_normalize(marker) for marker in event_markers}

    if normalized_markers & {"status changed", "status change", "status updated"}:
        return True

    update_markers = {"update", "updated", "issue update", "issue updated", "updated issue"}
    if normalized_markers & update_markers:
        return _updated_fields_include_status(payloads)

    return False


def _updated_fields_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        fields = payload.get("updatedFields") or payload.get("updated_fields")
        if isinstance(fields, str):
            values = [fields]
        elif isinstance(fields, (list, tuple, set)):
            values = [field for field in fields if isinstance(field, str)]
        else:
            continue

        if any(_normalize(field) in {"status", "state", "workflow state"} for field in values):
            return True
    return False


def _first_text(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in reversed(payloads):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_nested_text(
    payloads: list[Mapping[str, Any]],
    parent_keys: tuple[str, ...],
    child_key: str,
) -> str | None:
    for payload in reversed(payloads):
        for parent_key in parent_keys:
            value = payload.get(parent_key)
            if not isinstance(value, Mapping):
                continue
            child_value = value.get(child_key)
            if isinstance(child_value, str) and child_value.strip():
                return child_value
    return None


def _all_text(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                values.append(value)
    return values


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: str | None) -> str:
    if value is None:
        return ""

    split_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", split_camel).strip().casefold()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    """Read a JSON event from stdin and print the title update action, when any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON input: {exc}") from exc

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
