"""Build Linear issue title updates for Cursor research status changes.

The module is intentionally small and dependency-free so it can be used by
Cursor Automation glue code or tested directly from the command line.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b", re.IGNORECASE)
_CAMEL_CASE_BOUNDARY_RE = re.compile(r"([a-z0-9])([A-Z])")
_NON_WORD_RE = re.compile(r"[^A-Za-z0-9]+")

_NEW_STATUS_KEYS = {
    "newstatus",
    "newstatustype",
    "newstate",
    "newstatename",
    "newworkflowstate",
    "newworkflowstatename",
}
_STATUS_KEYS = {
    "status",
    "statusname",
    "statename",
    "state",
    "workflowstate",
    "workflowstatename",
}
_STATUS_CHANGE_KEYS = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}
_TITLE_KEYS = ("title", "issueTitle", "issue_title", "name")
_ISSUE_ID_KEYS = ("issueId", "issueID", "issue_id", "id", "identifier")


def normalize_status(value: Any) -> str:
    """Normalize a status value for matching regardless of casing/separators."""

    if value is None:
        return ""

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            if key in value:
                return normalize_status(value[key])
        return ""

    text = str(value).strip()
    text = _CAMEL_CASE_BOUNDARY_RE.sub(r"\1 \2", text)
    text = _NON_WORD_RE.sub(" ", text)
    return " ".join(text.lower().split())


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when the issue moved to research.

    The returned dictionary is deliberately plain JSON-serializable so callers
    can hand it to their Linear client of choice:

        {
            "action": "update_issue_title",
            "issueId": "POI-5039",
            "title": "Cursor researching: Hide default emissions ...",
        }
    """

    status = _extract_new_status(event)
    if normalize_status(status) != TARGET_STATUS:
        return None

    title = _extract_issue_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    if _PREFIX_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    for mapping in _candidate_mappings(event):
        for key, value in mapping.items():
            if _normalized_key(key) in _NEW_STATUS_KEYS:
                return _status_name(value)

    changed_status = _has_status_change_evidence(event)
    if changed_status:
        for mapping in _candidate_mappings(event):
            for key, value in mapping.items():
                if _normalized_key(key) in _STATUS_KEYS:
                    return _status_name(value)

        changed_value = _extract_changed_status_value(event)
        if changed_value:
            return changed_value

    return None


def _extract_changed_status_value(value: Any) -> Any:
    """Find the new status in common change-dictionary shapes."""

    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalized_key(key)
            if normalized_key in _STATUS_CHANGE_KEYS:
                if isinstance(child, Mapping):
                    for new_key in ("to", "new", "after", "toValue", "newValue", "name"):
                        if new_key in child:
                            return _status_name(child[new_key])
                else:
                    return _status_name(child)

            found = _extract_changed_status_value(child)
            if found:
                return found

    if isinstance(value, list):
        for item in value:
            found = _extract_changed_status_value(item)
            if found:
                return found

    return None


def _has_status_change_evidence(event: Mapping[str, Any]) -> bool:
    for mapping in _candidate_mappings(event):
        trigger = mapping.get("trigger") or mapping.get("triggerType") or mapping.get("action")
        if normalize_status(trigger) in {
            "status changed",
            "state changed",
            "workflow state changed",
            "status update",
        }:
            if _mapping_mentions_issue(mapping):
                return True

    return _has_status_change_key(event)


def _has_status_change_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalized_key(key)
            if normalized_key in {"changes", "changedfields", "updatedfields", "updatedfrom"}:
                if _change_container_mentions_status(child):
                    return True

            if _has_status_change_key(child):
                return True

    if isinstance(value, list):
        return any(_has_status_change_key(item) for item in value)

    return False


def _change_container_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalized_key(key) in _STATUS_CHANGE_KEYS
            or _change_container_mentions_status(child)
            for key, child in value.items()
        )

    if isinstance(value, list):
        return any(
            _normalized_key(item) in _STATUS_CHANGE_KEYS
            if isinstance(item, str)
            else _change_container_mentions_status(item)
            for item in value
        )

    return False


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    return _extract_string_field(event, _TITLE_KEYS)


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _extract_string_field(event, _ISSUE_ID_KEYS)


def _extract_string_field(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    normalized_keys = {_normalized_key(key) for key in keys}
    for mapping in _candidate_mappings(event):
        for key, value in mapping.items():
            if _normalized_key(key) not in normalized_keys:
                continue
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return None


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/event mappings in precedence order."""

    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        nested_trigger_context = automation_info.get("triggerContext")
        if isinstance(nested_trigger_context, Mapping):
            yield nested_trigger_context
        yield automation_info

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _mapping_mentions_issue(mapping: Mapping[str, Any]) -> bool:
    webhook_type = mapping.get("webhookType") or mapping.get("type")
    if normalize_status(webhook_type) == "issue":
        return True
    return any(_normalized_key(key) in {"issue", "issueid", "issuetitle"} for key in mapping)


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            if key in value:
                return value[key]
    return value


def _normalized_key(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value)).lower()


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
