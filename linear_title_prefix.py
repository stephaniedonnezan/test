"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_WORDS = ("status", "state", "workflow state")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research.

    The Cursor automation payload is usually a flat ``triggerContext`` object,
    while Linear webhooks can nest issue data under ``data.issue``. This handler
    accepts both shapes and returns ``None`` when no title update is needed.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_label(_extract_new_status(event)) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    contexts = _metadata_contexts(event)
    event_labels = [
        _normalize_label(value)
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event", "eventType")
        for value in [context.get(key)]
        if value is not None
    ]

    if any(_is_direct_status_change_label(label) for label in event_labels):
        return True

    if any(_is_update_label(label) for label in event_labels):
        return _has_status_updated_field(contexts)

    return False


def _is_direct_status_change_label(label: str) -> bool:
    return "change" in label and any(word in label for word in _DIRECT_STATUS_CHANGE_WORDS)


def _is_update_label(label: str) -> bool:
    words = set(label.split())
    return "update" in words or "updated" in words


def _has_status_updated_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    return any(_is_status_field_name(field) for context in contexts for field in _updated_field_names(context))


def _updated_field_names(context: Mapping[str, Any]) -> Iterable[str]:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        yield from _field_names_from_value(value)

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        yield from changes.keys()
    else:
        yield from _field_names_from_value(changes)


def _field_names_from_value(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, Mapping):
        yield from value.keys()
        field = value.get("field") or value.get("name")
        if field is not None:
            yield str(field)
        return

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                field = item.get("field") or item.get("name")
                if field is not None:
                    yield str(field)
                else:
                    yield from item.keys()
            else:
                yield str(item)


def _is_status_field_name(value: Any) -> bool:
    return _normalize_label(value) in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    contexts = _metadata_contexts(event)

    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
            "newState",
            "new_state",
        ):
            if key in context:
                return _name_from_value(context[key])

    changed_status = _status_from_changes(contexts)
    if changed_status is not None:
        return changed_status

    for context in _issue_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in context:
                return _name_from_value(context[key])

    return None


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for container_key in ("changes", "updatedFields", "updated_fields"):
            changes = context.get(container_key)
            if not isinstance(changes, Mapping):
                continue

            for field, value in changes.items():
                if not _is_status_field_name(field):
                    continue

                if isinstance(value, Mapping):
                    for key in ("to", "after", "new", "newValue", "new_value", "name"):
                        if key in value:
                            return _name_from_value(value[key])
                return _name_from_value(value)

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        for key in ("title", "issueTitle", "issue_title"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _metadata_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _unique_mappings(
        event,
        event.get("triggerContext"),
        event.get("data"),
        _mapping(event.get("data")).get("issue"),
        event.get("issue"),
    )


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return _unique_mappings(
        event.get("triggerContext"),
        _mapping(event.get("data")).get("issue"),
        event.get("issue"),
        event.get("data"),
        event,
    )


def _unique_mappings(*values: Any) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for value in values:
        if not isinstance(value, Mapping) or id(value) in seen:
            continue
        contexts.append(value)
        seen.add(id(value))
    return contexts


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _name_from_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""

    text = str(_name_from_value(value)).strip()
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
