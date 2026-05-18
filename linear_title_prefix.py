"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


ACTION = "update_issue_title"
PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"
RESEARCH_STATUS = "to research"

_STATUS_CHANGE_TOKENS = {
    "changed status",
    "issue status changed",
    "status change",
    "status changed",
}
_UPDATE_TOKENS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}
_STATUS_FIELD_TOKENS = {
    "state",
    "state id",
    "status",
    "status id",
    "workflow state",
    "workflow state id",
    "workflow status",
}
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "status",
    "state",
    "workflowState",
)
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action, or ``None`` if not applicable."""

    if not isinstance(event, Mapping):
        return None

    event_sources = _event_sources(event)
    issue_sources = _issue_sources(event)

    if not _is_status_change_event(event_sources):
        return None

    if _normalize_status(_first_status(event_sources, issue_sources)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(issue_sources, _ISSUE_ID_KEYS)
    title = _first_text(issue_sources, ("title",))
    if not issue_id or not title:
        return None

    if title.lstrip().lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": PREFIXED_TITLE_TEMPLATE.format(title=title),
    }


def _event_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources = [event]
    for path in (
        ("triggerContext",),
        ("data",),
        ("triggerContext", "data"),
        ("issue",),
        ("data", "issue"),
        ("triggerContext", "issue"),
        ("triggerContext", "data", "issue"),
    ):
        source = _mapping_at(event, path)
        if source is not None:
            sources.append(source)
    return _dedupe_mappings(sources)


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("triggerContext", "data", "issue"),
        ("triggerContext", "issue"),
        ("data",),
        (),
    ):
        source = event if not path else _mapping_at(event, path)
        if source is not None:
            sources.append(source)
    return _dedupe_mappings(sources)


def _mapping_at(
    mapping: Mapping[str, Any],
    path: tuple[str, ...],
) -> Mapping[str, Any] | None:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _dedupe_mappings(sources: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for source in sources:
        identity = id(source)
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(source)
    return deduped


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    has_update_event = False
    has_status_fields = False

    for source in sources:
        for key in _TRIGGER_KEYS:
            token = _normalize_token(source.get(key))
            if token in _STATUS_CHANGE_TOKENS:
                return True
            if token in _UPDATE_TOKENS:
                has_update_event = True

        if _updated_fields_include_status(source) or _updated_from_includes_status(source):
            has_status_fields = True

    return has_update_event and has_status_fields


def _updated_fields_include_status(source: Mapping[str, Any]) -> bool:
    for key in _UPDATED_FIELD_KEYS:
        fields = source.get(key)
        if isinstance(fields, str):
            field_values: Iterable[Any] = [fields]
        elif isinstance(fields, Iterable):
            field_values = fields
        else:
            continue

        for field in field_values:
            if _normalize_token(field) in _STATUS_FIELD_TOKENS:
                return True
    return False


def _updated_from_includes_status(source: Mapping[str, Any]) -> bool:
    updated_from = source.get("updatedFrom") or source.get("updated_from")
    if not isinstance(updated_from, Mapping):
        return False

    return any(_normalize_token(key) in _STATUS_FIELD_TOKENS for key in updated_from)


def _first_status(
    event_sources: Iterable[Mapping[str, Any]],
    issue_sources: Iterable[Mapping[str, Any]],
) -> str | None:
    explicit_status = _first_status_from_sources(event_sources, _NEW_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    return _first_status_from_sources(
        issue_sources,
        ("state", "workflowState", "status"),
    )


def _first_status_from_sources(
    sources: Iterable[Mapping[str, Any]],
    keys: Iterable[str],
) -> str | None:
    for source in sources:
        for key in keys:
            status = _status_text(source.get(key))
            if status:
                return status
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text(value.get(key))
            if text:
                return text

    return None


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            text = _text(source.get(key))
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_status(value: Any) -> str:
    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^0-9A-Za-z]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
