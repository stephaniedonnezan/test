"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_FIELDS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_text(
        _values_for_keys(
            contexts,
            (
                "newStatus",
                "new_status",
                "status",
                "state",
                "workflowState",
            ),
        )
    )
    if _normalize_text(new_status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue = _issue_context(contexts)
    issue_id = _first_text(
        _values_for_keys(
            (issue,),
            (
                "issueId",
                "issue_id",
                "identifier",
                "key",
                "id",
            ),
        )
    )
    title = _first_text(_values_for_keys((issue,), ("title", "name")))

    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            contexts.extend(_contexts(nested))
    return tuple(contexts)


def _issue_context(contexts: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    best: Mapping[str, Any] = {}
    for context in contexts:
        if _has_any_key(context, ("title", "name")) and _has_any_key(
            context,
            ("issueId", "issue_id", "identifier", "key", "id"),
        ):
            best = context
    return best


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = tuple(contexts)
    for value in _values_for_keys(
        contexts,
        (
            "trigger",
            "webhookType",
            "action",
            "type",
            "eventType",
        ),
    ):
        normalized = _normalize_text(_text_from(value))
        if normalized in {"status changed", "status change", "statuschanged"}:
            return True

    if not any(
        _normalize_text(_text_from(value)) in {"update", "updated", "issue updated"}
        for value in _values_for_keys(contexts, ("trigger", "action", "type", "eventType"))
    ):
        return False

    return any(_contains_status_change_field(context) for context in contexts)


def _contains_status_change_field(context: Mapping[str, Any]) -> bool:
    updated_fields = (
        context.get("updatedFields")
        or context.get("updated_fields")
        or context.get("changedFields")
        or context.get("changed_fields")
    )
    if isinstance(updated_fields, Iterable) and not isinstance(
        updated_fields,
        (str, bytes, Mapping),
    ):
        for field in updated_fields:
            if _normalize_field_name(str(field)) in _STATUS_CHANGE_FIELDS:
                return True

    changes = context.get("changes") or context.get("updatedFrom") or context.get("updated_from")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(str(key)) in _STATUS_CHANGE_FIELDS for key in changes)

    return False


def _values_for_keys(
    contexts: Iterable[Mapping[str, Any]],
    keys: Iterable[str],
) -> Iterable[Any]:
    contexts = tuple(contexts)
    for wanted_key in keys:
        normalized_key = _normalize_field_name(wanted_key)
        for context in contexts:
            for key, value in context.items():
                if _normalize_field_name(str(key)) == normalized_key:
                    yield value


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        text = _text_from(value)
        if text:
            return text
    return None


def _text_from(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(
            value.get(key)
            for key in (
                "name",
                "title",
                "label",
                "displayName",
                "identifier",
                "key",
                "id",
            )
        )
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_any_key(context: Mapping[str, Any], keys: Iterable[str]) -> bool:
    normalized_keys = {_normalize_field_name(key) for key in keys}
    return any(_normalize_field_name(str(key)) in normalized_keys for key in context)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", expanded.lower()).strip()


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_text(value))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
