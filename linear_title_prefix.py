"""Build Linear issue title updates for Cursor research automation triggers."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(payload: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The automation payload can be either the Cursor automation wrapper
    (`automation_trigger_info.triggerContext`), the direct trigger context, or a
    Linear-style webhook payload. The returned object is intentionally small so
    callers can adapt it to their Linear client of choice.
    """

    context = _trigger_context(payload)
    issue = _issue_data(context)
    title = _first_string(issue, context, keys=("title", "name"))
    issue_id = _first_string(issue, context, keys=("id", "issueId", "identifier"))

    if not title or not issue_id:
        return None

    if _has_research_prefix(title):
        return None

    if not _moved_to_research(context):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    automation_info = payload.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            return trigger_context

    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return payload


def _issue_data(context: Mapping[str, Any]) -> Mapping[str, Any]:
    data = context.get("data")
    if isinstance(data, Mapping):
        return data

    issue = context.get("issue")
    if isinstance(issue, Mapping):
        return issue

    return context


def _moved_to_research(context: Mapping[str, Any]) -> bool:
    return _is_status_change(context) and _normalized_status(_new_status(context)) == RESEARCH_STATUS


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger = _as_string(context.get("trigger"))
    if trigger and _normalize_token(trigger) in {"status changed", "status_changed"}:
        return True

    action = _as_string(context.get("action"))
    updated_from = context.get("updatedFrom")
    if action and _normalize_token(action) == "update" and isinstance(updated_from, Mapping):
        return any(key in updated_from for key in ("status", "state", "stateId", "workflowState"))

    if isinstance(updated_from, Mapping):
        return any(key in updated_from for key in ("status", "state", "stateId", "workflowState"))

    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    direct_status = _first_string(context, keys=("newStatus", "status"))
    if direct_status:
        return direct_status

    for key in ("state", "workflowState"):
        nested_status = _string_from_named_mapping(context.get(key))
        if nested_status:
            return nested_status

    data = context.get("data")
    if isinstance(data, Mapping):
        data_status = _first_string(data, keys=("newStatus", "status"))
        if data_status:
            return data_status

        for key in ("state", "workflowState"):
            nested_status = _string_from_named_mapping(data.get(key))
            if nested_status:
                return nested_status

    return None


def _first_string(*mappings: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = _as_string(mapping.get(key))
            if value:
                return value
    return None


def _string_from_named_mapping(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_string(value, keys=("name", "title"))
    return _as_string(value)


def _as_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalized_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_token(value)


def _normalize_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ").strip().lower())


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    payload = json.load(sys.stdin)
    if not isinstance(payload, Mapping):
        raise TypeError("Expected a JSON object payload")

    action = build_issue_title_update(payload)
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
