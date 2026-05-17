"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation trigger can pass either a flat context object or a nested
    Linear webhook payload. This function intentionally returns a plain action
    dictionary instead of performing side effects, leaving the caller to apply
    the issue update with its own Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_payloads(event))
    if not _is_status_change_event(candidates):
        return None

    if _normalize_status(_extract_new_status(candidates)) != TARGET_STATUS:
        return None

    issue_id = _extract_text(candidates, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_text(candidates, ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def buildIssueTitleUpdate(event: Mapping[str, Any]) -> dict[str, str] | None:
    """CamelCase compatibility wrapper for JavaScript-oriented callers."""

    return build_issue_title_update(event)


def _candidate_payloads(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload layers from highest to lowest priority for extraction."""

    nested_paths = (
        ("triggerContext",),
        ("triggerContext", "data", "issue"),
        ("triggerContext", "issue"),
        ("data", "issue"),
        ("issue",),
        ("data",),
        ("triggerContext", "data"),
    )

    seen: set[int] = set()
    for payload in (*(_get_path(event, path) for path in nested_paths), event):
        if isinstance(payload, Mapping) and id(payload) not in seen:
            seen.add(id(payload))
            yield payload


def _get_path(payload: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    event_words = {
        _normalize_words(str(value))
        for payload in candidates
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    }

    if event_words & {"status changed", "status change", "statuschanged"}:
        return True

    issue_update = bool(
        event_words
        & {
            "update",
            "updated",
            "issue update",
            "issue updated",
            "updated issue",
        }
    )
    return issue_update and _updated_fields_include_status(candidates)


def _updated_fields_include_status(candidates: list[Mapping[str, Any]]) -> bool:
    field_names = {"status", "state", "workflow state", "workflowstate"}
    for payload in candidates:
        for key in ("updatedFields", "updated_fields"):
            fields = payload.get(key)
            if isinstance(fields, str):
                fields = [fields]
            if isinstance(fields, Iterable) and not isinstance(fields, (bytes, Mapping)):
                for field in fields:
                    if _normalize_words(str(field)) in field_names:
                        return True

        for key in ("updatedFrom", "updated_from", "changes"):
            fields = payload.get(key)
            if isinstance(fields, Mapping):
                for field in fields:
                    if _normalize_words(str(field)) in field_names:
                        return True

    return False


def _extract_new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    direct_status = _extract_text(candidates, status_keys)
    if direct_status is not None:
        return direct_status

    for object_key in ("status", "state", "workflowState", "workflow_state"):
        nested_status = _extract_nested_name(candidates, object_key)
        if nested_status is not None:
            return nested_status

    return _extract_text(candidates, ("status", "state", "workflowState", "workflow_state"))


def _extract_nested_name(
    candidates: list[Mapping[str, Any]], object_key: str
) -> str | None:
    for payload in candidates:
        value = payload.get(object_key)
        if isinstance(value, Mapping):
            text = _string_or_none(value.get("name") or value.get("title"))
            if text is not None:
                return text
    return None


def _extract_text(
    candidates: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for payload in candidates:
        for key in keys:
            text = _string_or_none(payload.get(key))
            if text is not None:
                return text
    return None


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: str | None) -> str:
    if value is None:
        return ""
    return _normalize_words(value)


def _normalize_words(value: str) -> str:
    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"[^A-Za-z0-9]+", " ", camel_spaced)
    return " ".join(separated.lower().split())


def main() -> int:
    """Read a JSON event from stdin and write the update action as JSON."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
