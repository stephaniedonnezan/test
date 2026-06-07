"""Build Linear issue title updates for Cursor research automation.

The automation runner can pass either the flat Cursor trigger payload or a
Linear-style nested webhook payload.  This module keeps the decision pure so it
can be tested independently from whichever integration applies the returned
update action.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research.

    The returned shape is intentionally small and integration-agnostic:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    Non-matching payloads return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))

    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    issue = _extract_issue_identity(contexts)
    if issue is None:
        return None

    issue_id, title = issue
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue contexts, from specific to general."""

    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    for context in add(event):
        yield context

    for key in ("triggerContext", "trigger_context", "webhook", "payload"):
        for context in add(event.get(key)):
            yield context

    for parent_key in ("triggerContext", "trigger_context", "data", "payload", "webhook"):
        parent = event.get(parent_key)
        if not isinstance(parent, Mapping):
            continue
        for context in add(parent):
            yield context
        for child_key in ("issue", "data", "node"):
            for context in add(parent.get(child_key)):
                yield context

    for key in ("data", "issue", "node"):
        value = event.get(key)
        for context in add(value):
            yield context
        if isinstance(value, Mapping):
            for child_key in ("issue", "node"):
                for context in add(value.get(child_key)):
                    yield context


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)

    for context in contexts:
        for key in ("trigger", "event", "action", "type"):
            if _is_direct_status_change(context.get(key)):
                return True

    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes") or context.get("updatedFrom")
        if isinstance(changes, Mapping) and any(
            _normalize_field_name(field) in STATUS_FIELDS for field in changes
        ):
            return True

    return False


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_status(value)
    compact = normalized.replace(" ", "")
    return compact in {
        "statuschanged",
        "statechanged",
        "workflowstatechanged",
    }


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELDS

    if isinstance(value, Iterable):
        return any(_normalize_field_name(item) in STATUS_FIELDS for item in value)

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    contexts = list(contexts)
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )

    for key in explicit_status_keys:
        for context in contexts:
            value = context.get(key)
            if value not in (None, ""):
                return value

    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState", "workflow_state"):
                changed_value = changes.get(key)
                if isinstance(changed_value, Mapping):
                    for value_key in ("to", "new", "after", "name"):
                        value = changed_value.get(value_key)
                        if value not in (None, ""):
                            return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            extracted = _extract_name(value)
            if extracted not in (None, ""):
                return extracted

    return None


def _extract_issue_identity(contexts: Iterable[Mapping[str, Any]]) -> tuple[str, str] | None:
    issue_like = [context for context in contexts if _extract_title(context) is not None]

    for context in issue_like:
        issue_id = _extract_issue_id(context)
        title = _extract_title(context)
        if issue_id and title:
            return issue_id, title

    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = context.get(key)
        if value not in (None, ""):
            return str(value).strip() or None
    return None


def _extract_title(context: Mapping[str, Any]) -> str | None:
    value = context.get("title")
    if value in (None, ""):
        return None
    return str(value).strip() or None


def _extract_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if value.get(key) not in (None, ""):
                return value[key]
        return None
    return value


def _normalize_status(value: Any) -> str:
    value = _extract_name(value)
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-./]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize_status(value).replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 1

    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
