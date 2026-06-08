"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to To Research.

    The automation trigger payload can arrive as Cursor's ``triggerContext`` or
    as more direct Linear webhook shapes.  This function intentionally returns a
    serializable action instead of performing the API mutation so callers can
    decide how to dispatch it.
    """

    if not _is_status_change_event(event):
        return None

    status = _extract_status(event)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    title = _extract_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def main() -> int:
    """Read a JSON event from stdin and emit the requested update as JSON."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 1

    json.dump(update, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for source in _candidate_dicts(event):
        trigger = _first_string(source, ("trigger", "event", "eventType", "webhookType"))
        if _normalize_words(trigger) == "status changed":
            return True

        if source.get("statusChanged") is True or source.get("status_changed") is True:
            return True

    action = _first_string_from_event_candidates(event, ("action", "type"))
    if _normalize_words(action) in {"update", "issue updated", "updated"}:
        return _changed_fields_include_status(event)

    return _changed_fields_include_status(event)


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    status_fields = {"status", "state", "state id", "workflow state", "workflow state id"}

    for source in _candidate_dicts(event):
        for key in ("changedFields", "updatedFields"):
            value = source.get(key)
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
                if any(_normalize_words(item) in status_fields for item in value):
                    return True

        for key in ("changes", "updatedFrom", "previousValues"):
            value = source.get(key)
            if isinstance(value, Mapping):
                if any(_normalize_words(item) in status_fields for item in value.keys()):
                    return True

    return False


def _extract_status(event: Mapping[str, Any]) -> str | None:
    return _first_status_from_candidates(event, ("newStatus", "status", "state", "workflowState"))


def _extract_title(event: Mapping[str, Any]) -> str | None:
    return _first_string_from_candidates(event, ("title", "issueTitle"))


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_string_from_candidates(event, ("issueId", "id", "identifier"))


def _first_status_from_candidates(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for source in _issue_candidate_dicts(event):
        for key in keys:
            value = source.get(key)
            status = _status_to_string(value)
            if status:
                return status
    return None


def _first_string_from_candidates(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for source in _issue_candidate_dicts(event):
        value = _first_string(source, keys)
        if value:
            return value
    return None


def _first_string_from_event_candidates(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for source in _candidate_dicts(event):
        value = _first_string(source, keys)
        if value:
            return value
    return None


def _first_string(source: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _status_to_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if isinstance(value, Mapping):
        return _first_string(value, ("name", "title", "status"))

    return None


def _candidate_dicts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event/issue containers for event-metadata checks."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        yield value

        for key in ("triggerContext", "data", "issue"):
            child = value.get(key)
            if isinstance(child, Mapping):
                yield from visit(child)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield from visit(trigger_context)

    yield from visit(event)


def _issue_candidate_dicts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue containers before broader webhook envelope objects."""

    seen: set[int] = set()

    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
    ):
        value = _value_at_path(event, path)
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value


def _value_at_path(source: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = source
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_words(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-:/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


if __name__ == "__main__":
    raise SystemExit(main())
