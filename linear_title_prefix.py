"""Build Linear issue-title updates for research status changes.

The automation runner can pass either a compact trigger context or a nested
Linear webhook payload. This module keeps the decision pure: callers provide an
event dictionary and receive the title-update action to perform, or ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = ("newStatus", "new_status", "status", "state", "workflowState")
_TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")
_STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statuschange",
    "statuschanged",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_ISSUE_UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title-update action when the event qualifies.

    Qualifying events are status-change notifications whose new status is
    "to research". Existing titles that already start with the prefix are left
    unchanged.
    """

    if not isinstance(event, Mapping):
        return None

    sources = list(_iter_contexts(event))
    if not sources:
        return None

    if not _is_status_change_event(sources):
        return None

    status = _find_status(sources)
    if _normalize_words(status) != _normalize_words(TARGET_STATUS):
        return None

    issue_id = _find_string(sources, ("id", "issueId", "issue_id", "identifier"))
    title = _find_string(sources, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/trigger contexts from outermost to innermost data."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        yield value

        for key in ("triggerContext", "data", "issue", "node"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from visit(nested)

    yield from visit(event)


def _is_status_change_event(sources: list[Mapping[str, Any]]) -> bool:
    trigger_tokens = {
        _normalize_token(value)
        for source in sources
        for key in _TRIGGER_FIELDS
        if (value := _extract_name(source.get(key))) is not None
    }

    if trigger_tokens & _STATUS_CHANGE_TOKENS:
        return True

    if trigger_tokens & _ISSUE_UPDATE_TOKENS:
        return _updated_fields_include_status(sources)

    return False


def _updated_fields_include_status(sources: list[Mapping[str, Any]]) -> bool:
    for source in sources:
        raw_fields = (
            source.get("updatedFields")
            or source.get("updated_fields")
            or source.get("changedFields")
            or source.get("changed_fields")
        )
        fields = _iter_field_names(raw_fields)
        if any(
            _normalize_token(field) in {"status", "state", "workflowstate"}
            for field in fields
        ):
            return True
    return False


def _iter_field_names(raw_fields: Any) -> Iterable[str]:
    if isinstance(raw_fields, str):
        yield raw_fields
    elif isinstance(raw_fields, Mapping):
        yield from (str(key) for key in raw_fields)
    elif isinstance(raw_fields, Iterable):
        for field in raw_fields:
            field_name = _extract_name(field)
            if field_name:
                yield field_name


def _find_status(sources: list[Mapping[str, Any]]) -> str | None:
    for key in _STATUS_FIELDS:
        value = _find_value(sources, (key,))
        status = _extract_name(value)
        if status:
            return status
    return None


def _find_string(sources: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    value = _find_value(sources, keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _find_value(sources: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for source in sources:
        for key in keys:
            if key in source and source[key] not in (None, ""):
                return source[key]
    return None


def _extract_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _find_string([value], ("name", "title", "id", "key"))
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return " ".join(re.findall(r"[a-z0-9]+", spaced.casefold()))


def _normalize_token(value: str | None) -> str | None:
    words = _normalize_words(value)
    if words is None:
        return None
    return words.replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the resulting action as JSON."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
