"""Build Linear issue title updates for research status changes.

The automation runtime can import ``build_issue_title_update`` and apply the
returned action to Linear. The module also supports reading a JSON payload from
stdin for local/manual verification.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier", "key")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters to research.

    Returns ``None`` when the payload is not a status-change event, the new
    status is not "to research", required issue data is missing, or the title
    already starts with the expected prefix.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalize_status(_first_present(context, _NEW_STATUS_KEYS)) != "to research":
        return None

    issue_id = _clean_text(_first_present(context, _ISSUE_ID_KEYS))
    title = _clean_text(_first_present(context, ("title", "name")))
    if not issue_id or not title:
        return None

    if _title_has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely Linear/automation payload locations into one context."""

    context: dict[str, Any] = {}
    for source in _candidate_sources(event):
        context.update(source)
    return context


def _candidate_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested payload mappings from least to most specific."""

    sources: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            sources.append(value)

    data = event.get("data")
    trigger_context = event.get("triggerContext")

    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("data"))
        add(data)

    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))
        add(trigger_context)

    add(event.get("issue"))
    add(event)
    return sources


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    for key in _TRIGGER_KEYS:
        value = context.get(key)
        if _looks_like_status_changed(value):
            return True

    updated_fields = _first_present(
        context,
        ("updatedFields", "updated_fields", "changedFields", "changed_fields"),
    )
    return _contains_status_field(updated_fields)


def _looks_like_status_changed(value: Any) -> bool:
    normalized = _normalize_status(value)
    if normalized in {"status changed", "status change", "changed status"}:
        return True

    if normalized in {"issue updated", "updated issue", "update"}:
        return False

    return "status" in normalized and ("changed" in normalized or "change" in normalized)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_key(key) in _STATUS_FIELD_NAMES:
                return True
            if _contains_status_field(nested_value):
                return True
        return False

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_present(context: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in context and context[key] not in (None, ""):
            return context[key]
    return None


def _normalize_status(value: Any) -> str:
    text = _clean_text(_extract_named_value(value))
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_status(value))


def _extract_named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_present(value, ("name", "title", "label", "value"))
    return value


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _title_has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
