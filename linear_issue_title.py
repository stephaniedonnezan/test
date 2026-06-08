"""Derive Linear issue title updates for research status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any

RESEARCH_TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"

_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state updated",
    "workflow state changed",
    "workflow state updated",
}


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Return the prefixed title for a Linear status-change payload.

    ``None`` means the payload does not represent a move to ``to research`` or
    the current title already has the expected prefix.
    """

    contexts = list(_payload_contexts(payload))
    if not contexts or not _is_status_change_event(contexts):
        return None

    title = _first_text(contexts, ("title", "name"))
    new_status = _new_status(contexts)
    if title is None or new_status is None:
        return None

    updated_title = update_issue_title_for_status(title, new_status)
    if updated_title == title:
        return None
    return updated_title


def build_issue_title_update(payload: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a Linear issue title update action for automation runners."""

    updated_title = derive_updated_title(payload)
    if updated_title is None:
        return None

    issue_id = _first_text(
        _payload_contexts(payload),
        ("issueId", "issue_id", "identifier", "id"),
        reverse=True,
    )
    if issue_id is None:
        return None

    return {"issueId": issue_id, "title": updated_title}


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Prefix the title when ``new_status`` is ``to research``."""

    if _normalize(new_status) != RESEARCH_STATUS_NAME:
        return title
    return prefix_research_title(title)


def prefix_research_title(title: str) -> str:
    """Add the Cursor research prefix while avoiding duplicate prefixes."""

    if _PREFIX_PATTERN.match(title):
        return title

    stripped_title = title.strip()
    if not stripped_title:
        return RESEARCH_TITLE_PREFIX
    return f"{RESEARCH_TITLE_PREFIX} - {stripped_title}"


def _payload_contexts(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield nested payload contexts from most issue-specific to broadest."""

    if not isinstance(payload, Mapping):
        return

    trigger_context = _as_mapping(payload.get("triggerContext"))
    data = _as_mapping(payload.get("data"))
    issue = _as_mapping(payload.get("issue"))

    for container in (trigger_context, data):
        nested_issue = _as_mapping(container.get("issue")) if container else None
        if nested_issue:
            issue = nested_issue
            break

    seen: list[Mapping[str, Any]] = []
    for context in (issue, data, trigger_context, payload):
        if context and context not in seen:
            seen.append(context)
            yield context


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event"):
            value = context.get(key)
            if isinstance(value, str) and _normalize(value) in _STATUS_CHANGE_TRIGGERS:
                return True
    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    direct_status = _first_text(
        contexts,
        (
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
            "status",
            "state",
        ),
        reverse=True,
    )
    if direct_status is not None:
        return direct_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                status_name = _first_text([value], ("name", "title"))
                if status_name is not None:
                    return status_name
    return None


def _first_text(
    contexts: Iterable[Mapping[str, Any]],
    keys: tuple[str, ...],
    *,
    reverse: bool = False,
) -> str | None:
    ordered_contexts = list(contexts)
    if reverse:
        ordered_contexts.reverse()

    for context in ordered_contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _normalize(value: str) -> str:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _load_payload(input_path: str | None) -> Mapping[str, Any]:
    if input_path:
        with open(input_path, encoding="utf-8") as input_file:
            payload = json.load(input_file)
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise ValueError("Input payload must be a JSON object.")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive a Linear title update when status changes to to research."
    )
    parser.add_argument(
        "--input",
        help="Path to an input JSON payload. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input)
    print(json.dumps({"update": build_issue_title_update(payload)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
