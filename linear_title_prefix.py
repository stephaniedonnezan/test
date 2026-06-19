"""Build Linear issue title update actions for To Research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}
_STATUS_CHANGE_EVENTS = {"status change", "status changed"}
_GENERIC_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The automation layer consumes the returned dictionary and performs the
    actual Linear update. Non-matching or incomplete payloads return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    views = _payload_views(event)
    if not _is_status_change_event(views):
        return None

    new_status = _new_status(views)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(views, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(views, ("title", "name"))
    if not issue_id or not title:
        return None

    if _normalize(title).startswith(_normalize(TITLE_PREFIX)):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_views(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested payload maps ordered from most to least issue-specific."""

    views: list[Mapping[str, Any]] = []

    def add(value: Any) -> Mapping[str, Any] | None:
        if isinstance(value, Mapping) and value not in views:
            views.append(value)
            return value
        return value if isinstance(value, Mapping) else None

    root = add(event)
    trigger_context = add(root.get("triggerContext") if root else None)

    for source in (trigger_context, root):
        if not source:
            continue
        data = add(source.get("data"))
        issue = add(source.get("issue"))
        if data:
            add(data.get("issue"))
            add(data.get("node"))

    # Prefer issue details over enclosing webhook metadata for id/title/status.
    return list(reversed(views))


def _is_status_change_event(views: Iterable[Mapping[str, Any]]) -> bool:
    normalized_events = {
        _normalize(value)
        for view in views
        for key in ("trigger", "webhookType", "action", "type")
        if (value := view.get(key)) is not None
    }

    if normalized_events & _STATUS_CHANGE_EVENTS:
        return True

    if normalized_events & _GENERIC_UPDATE_EVENTS:
        return _updated_fields_include_status(views) or _changes_include_status(views)

    return False


def _updated_fields_include_status(views: Iterable[Mapping[str, Any]]) -> bool:
    for view in views:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "fields"):
            for field in _as_sequence(view.get(key)):
                if _normalize(field) in _STATUS_FIELD_NAMES:
                    return True
    return False


def _changes_include_status(views: Iterable[Mapping[str, Any]]) -> bool:
    for view in views:
        changes = view.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(key) in _STATUS_FIELD_NAMES for key in changes):
                return True
    return False


def _new_status(views: list[Mapping[str, Any]]) -> Any:
    changed_status = _changed_status_value(views)
    if changed_status is not None:
        return changed_status

    return _first_value(
        views,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )


def _changed_status_value(views: Iterable[Mapping[str, Any]]) -> Any:
    for view in views:
        changes = view.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _normalize(key) not in _STATUS_FIELD_NAMES:
                continue
            if isinstance(value, Mapping):
                for new_key in ("to", "new", "newValue", "new_value", "after", "value"):
                    if new_key in value:
                        return _name_or_text(value[new_key])
            else:
                return value

    return None


def _first_text(views: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    value = _first_value(views, keys)
    value = _name_or_text(value)
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _first_value(views: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for view in views:
        for key in keys:
            if key in view and view[key] is not None:
                return _name_or_text(view[key])
    return None


def _name_or_text(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if value.get(key) is not None:
                return value[key]
    return value


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable) and not isinstance(value, Mapping):
        return list(value)
    return [value]


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
