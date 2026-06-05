"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_label(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_text(contexts, ("issueTitle", "issue_title", "title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(data, "issue") if data else {}

    contexts: list[Mapping[str, Any]] = []
    for context in (trigger_context, event, data, issue):
        if context and context not in contexts:
            contexts.append(context)
    return contexts


def _mapping_at(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_update_event = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            event_name = _normalize_label(context.get(key))
            compact_event_name = event_name.replace(" ", "")
            if compact_event_name in {
                "statuschanged",
                "statechanged",
                "workflowstatechanged",
            }:
                return True
            if compact_event_name in {"update", "updated", "issueupdated", "updatedissue"}:
                saw_update_event = True

    return saw_update_event and _has_changed_status_field(contexts)


def _has_changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_has_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and _field_collection_has_status(changes.keys()):
            return True
        if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, Mapping)):
            if _field_collection_has_status(changes):
                return True

    return False


def _field_collection_has_status(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        fields = fields.keys()
    if isinstance(fields, (str, bytes)) or not isinstance(fields, Iterable):
        fields = (fields,)

    for field in fields:
        if isinstance(field, Mapping):
            field = (
                field.get("field")
                or field.get("name")
                or field.get("key")
                or field.get("property")
            )
        field_name = _normalize_label(field)
        if field_name in STATUS_FIELD_NAMES or field_name.replace(" ", "") in STATUS_FIELD_NAMES:
            return True
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    for context in contexts:
        value = _first_present(context, explicit_keys)
        if value is not None:
            return _status_value(value)

    changed_value = _status_from_changes(contexts)
    if changed_value is not None:
        return changed_value

    fallback_keys = ("status", "state", "workflowState", "workflow_state")
    for context in contexts:
        value = _first_present(context, fallback_keys)
        if value is not None:
            return _status_value(value)

    return None


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _is_status_field(key):
                    return _changed_value(value)
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            for change in changes:
                if isinstance(change, Mapping):
                    field = (
                        change.get("field")
                        or change.get("name")
                        or change.get("key")
                        or change.get("property")
                    )
                    if _is_status_field(field):
                        return _changed_value(change)
    return None


def _changed_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        changed = _first_present(
            value,
            (
                "newStatus",
                "new_status",
                "newValue",
                "new_value",
                "new",
                "to",
                "after",
                "current",
                "name",
                "value",
            ),
        )
        return _status_value(changed)
    return _status_value(value)


def _status_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_present(value, ("name", "title", "value", "status", "state"))
    return value


def _extract_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        value = _first_present(context, keys)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _first_present(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _is_status_field(value: Any) -> bool:
    field_name = _normalize_label(value)
    return field_name in STATUS_FIELD_NAMES or field_name.replace(" ", "") in STATUS_FIELD_NAMES


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _has_research_prefix(title: str) -> bool:
    return bool(re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE))


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
