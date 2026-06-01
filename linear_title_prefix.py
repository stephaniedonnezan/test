"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation trigger can provide a flat ``triggerContext`` payload or a
    nested Linear webhook shape. This function only decides what update should
    be applied; the caller remains responsible for applying it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id, title = _extract_issue_identity(contexts)
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload contexts from outermost to innermost."""

    yield event

    for key in ("triggerContext", "trigger_context", "payload", "webhook"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value
            yield from _iter_nested_issue_contexts(value)

    yield from _iter_nested_issue_contexts(event)


def _iter_nested_issue_contexts(context: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for key in ("data", "issue", "node"):
        value = context.get(key)
        if isinstance(value, Mapping):
            yield value
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                yield nested_issue


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if _has_status_changed_marker(contexts):
        return True

    if not _has_issue_update_marker(contexts):
        return False

    return _updated_fields_include_status(contexts)


def _has_status_changed_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    marker_keys = ("trigger", "webhookType", "webhook_type", "eventType", "event_type")
    for context in contexts:
        for key in marker_keys:
            marker = _normalize_words(context.get(key))
            if marker == "status changed" or marker.endswith(" status changed"):
                return True
    return False


def _has_issue_update_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    marker_keys = ("action", "type", "trigger", "webhookType", "webhook_type", "eventType", "event_type")
    for context in contexts:
        for key in marker_keys:
            marker = _normalize_words(context.get(key))
            if marker in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                return True
            if marker in {"issue.updated", "issue updated"}:
                return True
    return False


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            if _field_collection_includes_status(value):
                return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping) and _field_collection_includes_status(updated_from.keys()):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        fields = [value]
    elif isinstance(value, Mapping):
        fields = value.keys()
    elif isinstance(value, Iterable):
        fields = value
    else:
        return False

    for field in fields:
        normalized = _normalize_field_name(field)
        if normalized in STATUS_FIELD_NAMES or normalized.endswith(" status"):
            return True
        if normalized in {"stateid", "state id", "workflowstateid", "workflow state id"}:
            return True
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status = _first_text(contexts, explicit_keys)
    if status is not None:
        return status

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _text(value.get("name"))
                if name is not None:
                    return name
            else:
                text = _text(value)
                if text is not None:
                    return text

    return None


def _extract_issue_identity(contexts: Iterable[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    contexts = list(contexts)
    id_keys = ("id", "issueId", "issue_id", "identifier")
    title_keys = ("title", "name")

    for context in contexts:
        issue_id = _first_text((context,), id_keys)
        title = _first_text((context,), title_keys)
        if issue_id is not None and title is not None:
            return issue_id, title

    return _first_text(contexts, id_keys), _first_text(contexts, title_keys)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text is not None:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.casefold().split())


def _normalize_field_name(value: Any) -> str:
    return _normalize_words(str(value) if value is not None else "")


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
