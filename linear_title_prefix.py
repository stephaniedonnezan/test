"""Build Linear issue title updates for research status changes.

The automation runner can import ``build_issue_title_update`` or pipe a JSON
payload into this module as a small CLI. The function is intentionally pure so
it is straightforward to test without calling Linear.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state", "workflow_status"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    Supported payload shapes include the flat automation ``triggerContext``
    object and common nested Linear webhook forms under ``data`` or ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merge_context(event)
    if not _is_status_change(context):
        return None

    status = _extract_new_status(context)
    if _normalize_label(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_first_text(context, ("issueId", "issue_id", "identifier", "id"))
    title = _extract_first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _merge_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common wrapper objects while letting outer metadata win."""

    context: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_merge_context(value))

    # Preserve direct event keys over nested issue fields, which matters for
    # status-change metadata such as newStatus.
    context.update(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized_values = {_normalize_event_name(value) for value in trigger_values if value}

    if "statuschanged" in normalized_values:
        return True

    if {"update", "issueupdated", "updatedissue"} & normalized_values:
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = list(updated_fields)
    elif isinstance(updated_fields, list | tuple | set):
        fields = list(updated_fields)
    else:
        return False

    for field in fields:
        if _normalize_key(field) in STATUS_FIELD_NAMES:
            return True
    return False


def _extract_new_status(context: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = context.get(key)
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested = _extract_first_text(value, ("name", "title", "status"))
            if nested:
                return nested
        elif value:
            return value

    return None


def _extract_first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if value is not None and not isinstance(value, Mapping | list | tuple | set):
            text = str(value).strip()
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_label(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _extract_first_text(value, ("name", "title", "status"))
    if value is None:
        return ""
    return " ".join(_split_words(str(value))).casefold()


def _normalize_event_name(value: Any) -> str:
    return "".join(_split_words(str(value))).casefold()


def _normalize_key(value: Any) -> str:
    return "_".join(_split_words(str(value))).casefold()


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return [part for part in re.split(r"[\s_\-:.]+", spaced) if part]


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0

    json.dump(update, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
