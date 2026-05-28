"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
CHANGE_SIGNAL_KEYS = {"trigger", "action", "type", "webhooktype", "webhook_type"}
STATUS_CHANGE_SIGNALS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
UPDATE_SIGNALS = {"update", "updated", "issue update", "issue updated", "updated issue"}
NEW_STATUS_KEYS = {
    "newstatus",
    "new_status",
    "tostatus",
    "to_status",
    "statusto",
    "state_to",
    "stateto",
    "workflowstateto",
    "workflow_state_to",
}
ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    contexts = _gather_contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _gather_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
            add(trigger_data)

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    if any(_updated_fields_include_status(context.get("updatedFields")) for context in contexts):
        return True

    for context in contexts:
        for key, value in context.items():
            if not isinstance(value, str) or _compact_key(key) not in CHANGE_SIGNAL_KEYS:
                continue

            signal = _normalize(value)
            if signal in STATUS_CHANGE_SIGNALS:
                return True
            if signal in UPDATE_SIGNALS and any(
                _updated_fields_include_status(candidate.get("updatedFields"))
                for candidate in contexts
            ):
                return True

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _status_from_updated_fields(context.get("updatedFields"))
        if status is not None:
            return status

    for context in contexts:
        for key, value in context.items():
            if _compact_key(key) in NEW_STATUS_KEYS:
                status = _coerce_name(value)
                if status is not None:
                    return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_name(context.get(key))
            if status is not None:
                return status

    return None


def _status_from_updated_fields(updated_fields: Any) -> str | None:
    if isinstance(updated_fields, Mapping):
        for key, value in updated_fields.items():
            if _compact_key(key) not in STATUS_FIELDS:
                continue

            if isinstance(value, Mapping):
                for target_key in ("to", "new", "after", "name"):
                    status = _coerce_name(value.get(target_key))
                    if status is not None:
                        return status
            else:
                status = _coerce_name(value)
                if status is not None:
                    return status

    if isinstance(updated_fields, list):
        for item in updated_fields:
            if not isinstance(item, Mapping):
                continue

            field_name = item.get("field") or item.get("name") or item.get("key")
            if _compact_key(field_name) not in STATUS_FIELDS:
                continue

            for target_key in ("to", "new", "after", "value"):
                status = _coerce_name(item.get(target_key))
                if status is not None:
                    return status

    return None


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, Mapping):
        return any(_compact_key(key) in STATUS_FIELDS for key in updated_fields)

    if isinstance(updated_fields, list):
        for item in updated_fields:
            if isinstance(item, str) and _compact_key(item) in STATUS_FIELDS:
                return True

            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if _compact_key(field_name) in STATUS_FIELDS:
                    return True

    return False


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ISSUE_ID_KEYS:
            issue_id = context.get(key)
            if issue_id is not None and str(issue_id).strip():
                return str(issue_id).strip()
    return None


def _extract_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        title = context.get("title")
        if title is not None and str(title).strip():
            return str(title)
    return None


def _coerce_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status"):
            status = _coerce_name(value.get(key))
            if status is not None:
                return status
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _compact_key(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
