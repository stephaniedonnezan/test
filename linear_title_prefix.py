"""Build Linear issue title updates for research status changes.

The automation runner passes Linear webhook or Cursor trigger payloads to
``build_issue_title_update``. When the payload represents an issue status
change to "to research", the function returns the title update action the
runner can send to Linear.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_STATUS_CHANGE_KEYS = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "changed",
    "updatedFrom",
    "updated_from",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for status changes to research.

    The result is intentionally side-effect free. A caller that owns Linear API
    access can apply the returned ``issueId`` and ``title``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(event, contexts):
        return None

    if _normalise_status(_extract_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, _ISSUE_ID_KEYS)
    title = _extract_first_text(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload sections most likely to contain issue metadata."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        for issue_key in ("issue", "node"):
            issue = data.get(issue_key)
            if isinstance(issue, Mapping):
                yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _is_status_change_event(
    event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]
) -> bool:
    if any(_is_explicit_status_change(context.get(key)) for context in contexts for key in _EVENT_KEYS):
        return True

    if _has_generic_issue_update(contexts) and any(
        _contains_status_change_field(context.get(key))
        for context in (event, *contexts)
        for key in _UPDATED_FIELD_KEYS
    ):
        return True

    return False


def _is_explicit_status_change(value: Any) -> bool:
    token = _normalise_token(value)
    return "status" in token and ("change" in token or "changed" in token)


def _has_generic_issue_update(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_tokens = {
        _normalise_token(context.get(key))
        for context in contexts
        for key in _EVENT_KEYS
    }
    return bool(
        {"update", "updated", "issueupdate", "issueupdated", "updatedissue"} & event_tokens
    )


def _contains_status_change_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalise_token(key) in _STATUS_CHANGE_KEYS
            or _contains_status_change_field(nested_value)
            for key, nested_value in value.items()
        )

    if isinstance(value, str):
        return _normalise_token(value) in _STATUS_CHANGE_KEYS

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_change_field(item) for item in value)

    return False


def _extract_status(contexts: Sequence[Mapping[str, Any]]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        value = _extract_value(contexts, key)
        if value is not None:
            return value

    for key in _STATUS_KEYS:
        value = _extract_value(contexts, key)
        if value is not None:
            return value

    return None


def _extract_value(contexts: Sequence[Mapping[str, Any]], key: str) -> Any:
    for context in contexts:
        if key in context and context[key] is not None:
            return context[key]
    return None


def _extract_first_text(
    contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalise_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            normalised = _normalise_status(value.get(key))
            if normalised:
                return normalised
        return None

    if not isinstance(value, str):
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text) if text else None


def _normalise_token(value: Any) -> str:
    normalised = _normalise_status(value)
    return re.sub(r"[^a-z0-9]+", "", normalised or "")


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
