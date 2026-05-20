"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATOR_RE = re.compile(r"[\s_-]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    containers = list(_iter_payload_containers(event))
    if not _is_status_change_event(containers):
        return None

    status = _extract_status(containers)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(containers, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_first_text(containers, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _iter_payload_containers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/trigger mappings from flat and nested payload shapes."""

    yield event

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            yield nested

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            nested = trigger_context.get(key)
            if isinstance(nested, Mapping):
                yield nested

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "workflowState"):
            nested = data.get(key)
            if isinstance(nested, Mapping):
                yield nested

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        for key in ("state", "workflowState", "status"):
            nested = issue.get(key)
            if isinstance(nested, Mapping):
                yield nested


def _is_status_change_event(containers: Iterable[Mapping[str, Any]]) -> bool:
    containers = list(containers)

    for container in containers:
        for key in ("trigger", "eventType", "webhookType", "type"):
            value = _normalize(container.get(key))
            if value in {"status changed", "state changed", "workflow state changed"}:
                return True
            if value.endswith(" status changed") or value.endswith(" state changed"):
                return True

    for container in containers:
        action = _normalize(container.get("action"))
        if action in {"update", "updated", "issue updated", "updated issue"}:
            updated_fields = container.get("updatedFields", container.get("updated_fields"))
            if _contains_status_field(updated_fields):
                return True

    return False


def _extract_status(containers: Iterable[Mapping[str, Any]]) -> str | None:
    containers = list(containers)

    for key in ("newStatus", "new_status", "newState", "new_state", "toStatus", "to_status"):
        status = _extract_first_text(containers, (key,))
        if status:
            return status

    for container in containers:
        for key in ("status", "state", "workflowState"):
            value = container.get(key)
            if isinstance(value, Mapping):
                name = _text(value.get("name"))
                if name:
                    return name
            else:
                status = _text(value)
                if status:
                    return status

    return None


def _extract_first_text(containers: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for container in containers:
        for key in keys:
            value = _text(container.get(key))
            if value:
                return value
    return None


def _contains_status_field(value: Any) -> bool:
    for field in _iter_field_names(value):
        normalized = _normalize(field)
        if normalized in {"status", "state", "workflow state"}:
            return True
    return False


def _iter_field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, nested_value in value.items():
            yield str(key)
            yield from _iter_field_names(nested_value)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            yield from _iter_field_names(item)


def _normalize(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""

    text = _CAMEL_BOUNDARY_RE.sub(" ", text.strip())
    return _SEPARATOR_RE.sub(" ", text).strip().casefold()


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
