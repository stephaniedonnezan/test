"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action when an issue moves to research.

    The automation payloads may be either the flat Cursor trigger context shape or
    nested Linear webhook shapes. Returning ``None`` means no title update is
    needed for the event.
    """
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _new_status(context)
    if _normalize(new_status) != _normalize(TARGET_STATUS):
        return None

    issue = _issue_data(event, context)
    issue_id = _first_text(issue, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(issue, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_title_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the payload areas that commonly hold trigger metadata."""
    context: dict[str, Any] = {}
    for candidate in _mapping_candidates(event):
        context.update(candidate)
    return context


def _mapping_candidates(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    for key in ("triggerContext", "webhook", "payload", "data", "issue"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            yield from _mapping_candidates(nested)

    yield value


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized_values = {_normalize(value) for value in trigger_values if value}

    if "status changed" in normalized_values or "status change" in normalized_values:
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in normalized_values):
        return _updated_status_fields(context)

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    updated_fields = (
        context.get("updatedFields")
        or context.get("updatedFieldNames")
        or context.get("changedFields")
        or context.get("changes")
    )
    if not updated_fields:
        return False

    if isinstance(updated_fields, Mapping):
        field_names = updated_fields.keys()
    elif isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (str, bytes)):
        field_names = updated_fields
    else:
        field_names = (updated_fields,)

    return any(_normalize(field) in _STATUS_FIELD_NAMES for field in field_names)


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = context.get(key)
        text = _text_or_name(value)
        if text:
            return text

    for key in ("state", "workflowState"):
        value = context.get(key)
        text = _text_or_name(value)
        if text:
            return text

    text = _text_or_name(context.get("status"))
    if text:
        return text

    return None


def _issue_data(event: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("issue", "data"):
        value = event.get(key)
        if isinstance(value, Mapping) and _first_text(value, ("title", "name")):
            return value

    return context


def _first_text(data: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        text = _text_or_name(data.get(key))
        if text:
            return text
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "id"))
    return None


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", camel_spaced.casefold()).strip()


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is None:
        return 0

    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
