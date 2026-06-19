"""Build Linear issue-title updates for Cursor research status transitions.

The automation platform passes different payload shapes depending on whether
the event comes from Cursor's trigger context or directly from Linear's webhook.
This module keeps the title-prefix rule isolated and testable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_CHANGE_KEYS = {"status", "state", "workflowstate", "stateid", "statusid"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research.

    The function is intentionally side-effect free so callers can decide how to
    apply the update through their Linear client. It returns ``None`` when the
    payload does not represent a status change to "to research" or when the
    issue title is already prefixed.
    """

    payloads = _candidate_payloads(event)
    if not _changed_to_research(payloads):
        return None

    issue_id = _first_text(payloads, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(payloads, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        _append_mapping(payloads, event.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "workflowState"):
            _append_mapping(payloads, data.get(key))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        for key in ("state", "workflowState"):
            _append_mapping(payloads, issue.get(key))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue", "state", "workflowState"):
            _append_mapping(payloads, trigger_context.get(key))

        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            _append_mapping(payloads, trigger_data.get("issue"))

    return payloads


def _append_mapping(payloads: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping):
        payloads.append(value)


def _changed_to_research(payloads: Sequence[Mapping[str, Any]]) -> bool:
    if _new_status(payloads) != RESEARCH_STATUS:
        return False

    if _has_explicit_status_change_trigger(payloads):
        return True

    return any(_mentions_status_change(payload) for payload in payloads)


def _new_status(payloads: Sequence[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        for key in ("newStatus", "new_status", "status", "state", "workflowState"):
            value = payload.get(key)
            status = _status_name(value)
            if status:
                return status

    for payload in payloads:
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState"):
                change = changes.get(key)
                if isinstance(change, Mapping):
                    status = _status_name(
                        change.get("to")
                        or change.get("new")
                        or change.get("current")
                        or change.get("after")
                    )
                    if status:
                        return status

    return None


def _status_name(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state"):
            status = _status_name(value.get(key))
            if status:
                return status
        return None

    if isinstance(value, str):
        normalized = _normalize_status(value)
        return normalized or None

    return None


def _normalize_status(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[\W_]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _has_explicit_status_change_trigger(payloads: Sequence[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        trigger = payload.get("trigger") or payload.get("event") or payload.get("action")
        if isinstance(trigger, str) and _normalize_status(trigger) in {
            "status changed",
            "status change",
            "state changed",
            "state change",
        }:
            return True

        webhook_type = payload.get("webhookType") or payload.get("type")
        if isinstance(webhook_type, str) and _normalize_status(webhook_type) == "issue":
            if "newStatus" in payload or "new_status" in payload:
                return True

    return False


def _mentions_status_change(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        if _sequence_mentions_status(payload.get(key)):
            return True

    for key in ("updatedFrom", "previous", "previousValue", "previousValues", "changes"):
        value = payload.get(key)
        if isinstance(value, Mapping) and any(_is_status_key(status_key) for status_key in value):
            return True

    return False


def _sequence_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_key(value)

    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False

    return any(isinstance(item, str) and _is_status_key(item) for item in value)


def _is_status_key(value: str) -> bool:
    return _normalize_status(value).replace(" ", "") in STATUS_CHANGE_KEYS


def _first_text(payloads: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit a Linear title update when an issue moves to 'to research'."
    )
    parser.add_argument(
        "event",
        nargs="?",
        help="Path to a JSON event payload. Reads stdin when omitted.",
    )
    args = parser.parse_args(argv)

    try:
        if args.event:
            with open(args.event, encoding="utf-8") as event_file:
                event = json.load(event_file)
        else:
            event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(event, Mapping):
        print("event payload must be a JSON object", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    print(json.dumps(update or {}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
