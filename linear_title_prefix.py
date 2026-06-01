"""Build Linear issue title updates for research-status automation.

The automation is intentionally side-effect free: callers pass a Linear-style
webhook payload and receive the issue title update they should apply, or None.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when an issue status changes to "to research"."""
    if not isinstance(event, Mapping):
        return None

    context = _flatten_context(event)

    if not _is_status_change(context):
        return None

    if _normalize_text(_extract_new_status(context)) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_text(context, ("title", "name"))

    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common webhook nesting shapes while keeping top-level fields first."""
    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, item in value.items():
                context.setdefault(str(key), item)

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            for inner_key in ("issue", "data"):
                inner = nested.get(inner_key)
                if isinstance(inner, Mapping):
                    merge(inner)
            merge(nested)

    merge(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get(key)
        for key in ("trigger", "webhookType", "action", "type")
        if key in context
    ]

    if any(_normalize_text(value) in {"status changed", "statuschanged"} for value in trigger_values):
        return True

    normalized_triggers = {_normalize_text(value) for value in trigger_values}
    if normalized_triggers & {"update", "issue updated", "updated issue"}:
        updated_fields = _updated_field_names(context.get("updatedFields") or context.get("updated_fields"))
        return bool(updated_fields & STATUS_FIELDS)

    return False


def _extract_new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status"):
        value = context.get(key)
        if value is not None:
            return _extract_name(value)

    for key in ("state", "workflowState", "workflow_state"):
        value = context.get(key)
        name = _extract_name(value)
        if name is not None:
            return name

    return None


def _extract_first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if value is None:
            continue

        value = _extract_name(value)
        if value is None:
            continue

        text = str(value).strip()
        if text:
            return text

    return None


def _extract_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name")
    return value


def _updated_field_names(value: Any) -> set[str]:
    if value is None:
        return set()

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Mapping):
        values = value.keys()
    else:
        try:
            values = list(value)
        except TypeError:
            return set()

    return {_normalize_field_name(item) for item in values}


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _camel_to_words(str(value)).lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = _camel_to_words(str(_extract_name(value)))
    return re.sub(r"[\s_-]+", " ", text).strip().lower()


def _camel_to_words(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
