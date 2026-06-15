"""Build Linear issue title updates for Cursor research status changes.

The Cursor automation payloads used for Linear issues can arrive as a flat
``triggerContext`` object or as a raw Linear webhook payload.  This module keeps
the title update logic small and deterministic so the automation can decide
whether an issue title should be changed.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"
UPDATE_ACTION = "update_issue_title"


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalize_token(value: Any) -> str:
    return _normalize_whitespace(str(value).replace("_", " ").replace("-", " ")).lower()


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _normalize_whitespace(value.strip())
    return _normalize_whitespace(str(value).strip())


def _context_candidates(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely locations for Linear issue/status data in priority order."""

    trigger_context = payload.get("triggerContext")
    if _is_mapping(trigger_context):
        yield trigger_context

    yield payload

    for key in ("issue", "data"):
        value = payload.get(key)
        if _is_mapping(value):
            yield value

    if _is_mapping(trigger_context):
        for key in ("issue", "data"):
            value = trigger_context.get(key)
            if _is_mapping(value):
                yield value


def _status_name(value: Any) -> str:
    if _is_mapping(value):
        for key in ("name", "title", "label", "status"):
            candidate = _status_name(value.get(key))
            if candidate:
                return candidate
        return ""
    return _string_value(value)


def _extract_changed_status(changes: Any) -> str:
    if not _is_mapping(changes):
        return ""

    for key in ("status", "state", "stateId", "state_id"):
        change = changes.get(key)
        if not _is_mapping(change):
            candidate = _status_name(change)
            if candidate:
                return candidate
            continue

        for new_value_key in ("to", "new", "after", "current", "value"):
            candidate = _status_name(change.get(new_value_key))
            if candidate:
                return candidate

    return ""


def _extract_new_status(payload: Mapping[str, Any]) -> str:
    for context in _context_candidates(payload):
        for key in ("newStatus", "status", "state"):
            candidate = _status_name(context.get(key))
            if candidate:
                return candidate

        for key in ("changes", "change"):
            candidate = _extract_changed_status(context.get(key))
            if candidate:
                return candidate

    return ""


def _extract_title(payload: Mapping[str, Any]) -> str:
    for context in _context_candidates(payload):
        candidate = _string_value(context.get("title"))
        if candidate:
            return candidate
    return ""


def _extract_issue_id(payload: Mapping[str, Any]) -> str:
    for context in _context_candidates(payload):
        for key in ("issueId", "issueID", "id", "identifier"):
            candidate = _string_value(context.get(key))
            if candidate:
                return candidate
    return ""


def _field_names(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_token(value)}
    if not isinstance(value, Iterable) or _is_mapping(value):
        return set()

    names: set[str] = set()
    for item in value:
        if _is_mapping(item):
            for key in ("name", "field", "key"):
                candidate = _string_value(item.get(key))
                if candidate:
                    names.add(_normalize_token(candidate))
        else:
            candidate = _string_value(item)
            if candidate:
                names.add(_normalize_token(candidate))
    return names


def _has_status_change_field(fields: set[str]) -> bool:
    return any(field in {"status", "state", "stateid", "state id"} for field in fields)


def _is_status_change_trigger(value: Any) -> bool:
    token = _normalize_token(value)
    if not token:
        return False
    return ("status" in token or "state" in token) and (
        "change" in token or "changed" in token or "update" in token or "updated" in token
    )


def _is_status_change_payload(payload: Mapping[str, Any]) -> bool:
    explicit_trigger_seen = False

    for context in _context_candidates(payload):
        for key in ("trigger", "event", "eventType", "type"):
            trigger_value = context.get(key)
            if trigger_value:
                explicit_trigger_seen = True
                if _is_status_change_trigger(trigger_value):
                    return True

        for key in ("updatedFields", "changedFields"):
            if _has_status_change_field(_field_names(context.get(key))):
                return True

        for key in ("changes", "change", "updatedFrom"):
            value = context.get(key)
            if _is_mapping(value) and _has_status_change_field({_normalize_token(field) for field in value}):
                return True

    if explicit_trigger_seen:
        return False

    # Some automation invocations pass only the new status and title.  Treat
    # those as status-change inputs when no contradictory trigger is present.
    return bool(_extract_new_status(payload))


def _title_has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(RESEARCH_TITLE_PREFIX.lower())


def update_issue_title_for_status(title: str, new_status: str) -> str | None:
    """Return the prefixed title for a transition to ``to research``.

    ``None`` means no update should be sent.
    """

    normalized_status = _normalize_token(new_status)
    normalized_title = _string_value(title)
    if normalized_status != RESEARCH_STATUS_NAME or not normalized_title:
        return None
    if _title_has_research_prefix(normalized_title):
        return None
    return f"{RESEARCH_TITLE_PREFIX}: {normalized_title}"


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Return the updated title for a Linear/Cursor payload, if needed."""

    if not _is_mapping(payload) or not _is_status_change_payload(payload):
        return None
    return update_issue_title_for_status(_extract_title(payload), _extract_new_status(payload))


def build_issue_title_update(payload: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the issue-title update action for the automation runner."""

    if not _is_mapping(payload):
        return None

    title = derive_updated_title(payload)
    issue_id = _extract_issue_id(payload)
    if not title or not issue_id:
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": title,
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
