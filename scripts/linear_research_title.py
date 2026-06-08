#!/usr/bin/env python3
"""Update a Linear issue title when it moves to To Research.

The script is intended for a Cursor Automation triggered by Linear issue status
changes. It reads the trigger payload from a file, stdin, or environment, and
prefixes the issue title with "Cursor researching" when the new status is
"to research".
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


TITLE_MARKER = "Cursor researching"
TITLE_PREFIX = f"{TITLE_MARKER}: "
TARGET_STATUS = "to research"
DEFAULT_LINEAR_API_URL = "https://api.linear.app/graphql"


@dataclass(frozen=True)
class TitleUpdate:
    """The Linear issue title update that should be sent."""

    issue_id: str
    old_title: str
    new_title: str


def normalize_status(status: object) -> str:
    """Normalize a status name for case-insensitive comparisons."""

    if not isinstance(status, str):
        return ""
    return " ".join(status.replace("_", " ").replace("-", " ").strip().lower().split())


def trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return the Cursor trigger context when present, otherwise the payload."""

    context = payload.get("triggerContext")
    return context if isinstance(context, Mapping) else payload


def nested_get(mapping: Mapping[str, Any], *keys: str) -> object:
    """Safely read a nested value from dictionaries."""

    current: object = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def is_issue_status_change(payload: Mapping[str, Any]) -> bool:
    """Determine whether a payload describes an issue status change."""

    context = trigger_context(payload)

    webhook_type = context.get("webhookType") or context.get("type")
    if isinstance(webhook_type, str) and webhook_type.lower() not in {"issue", "issueupdate"}:
        return False

    trigger = context.get("trigger")
    if isinstance(trigger, str) and trigger.lower() != "status_changed":
        return False

    action = context.get("action")
    if isinstance(action, str) and action.lower() not in {"update", "status_changed"}:
        return False

    return True


def new_status_name(payload: Mapping[str, Any]) -> str:
    """Extract the destination status from Cursor or Linear webhook payloads."""

    context = trigger_context(payload)
    candidates = (
        context.get("newStatus"),
        context.get("status"),
        nested_get(context, "state", "name"),
        nested_get(context, "data", "state", "name"),
    )
    for candidate in candidates:
        normalized = normalize_status(candidate)
        if normalized:
            return normalized
    return ""


def issue_id(payload: Mapping[str, Any]) -> str:
    """Extract a Linear issue ID from supported payload shapes."""

    context = trigger_context(payload)
    candidates = (
        context.get("id"),
        context.get("issueId"),
        nested_get(context, "issue", "id"),
        nested_get(context, "data", "id"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def issue_title(payload: Mapping[str, Any]) -> str:
    """Extract the current issue title from supported payload shapes."""

    context = trigger_context(payload)
    candidates = (
        context.get("title"),
        nested_get(context, "issue", "title"),
        nested_get(context, "data", "title"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return ""


def title_update_for_payload(payload: Mapping[str, Any]) -> TitleUpdate | None:
    """Build the title update needed for a qualifying status change."""

    if not is_issue_status_change(payload):
        return None

    if new_status_name(payload) != TARGET_STATUS:
        return None

    current_title = issue_title(payload)
    linear_issue_id = issue_id(payload)
    if not current_title or not linear_issue_id:
        return None

    if TITLE_MARKER.lower() in current_title.lower():
        return None

    return TitleUpdate(
        issue_id=linear_issue_id,
        old_title=current_title,
        new_title=f"{TITLE_PREFIX}{current_title}",
    )


def read_payload(args: argparse.Namespace) -> Mapping[str, Any]:
    """Read JSON payload from file, stdin, or supported environment variables."""

    raw_payload = ""
    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as payload_file:
            raw_payload = payload_file.read()
    elif not sys.stdin.isatty():
        raw_payload = sys.stdin.read()
    else:
        for env_name in (
            "AUTOMATION_TRIGGER_INFO",
            "CURSOR_AUTOMATION_TRIGGER_INFO",
            "LINEAR_WEBHOOK_PAYLOAD",
        ):
            raw_payload = os.environ.get(env_name, "")
            if raw_payload:
                break

    if not raw_payload.strip():
        raise ValueError(
            "No payload provided. Pass --payload-file, pipe JSON on stdin, or set "
            "AUTOMATION_TRIGGER_INFO."
        )

    payload = json.loads(raw_payload)
    if not isinstance(payload, Mapping):
        raise ValueError("Payload must be a JSON object.")
    return payload


def update_linear_issue_title(
    update: TitleUpdate,
    api_key: str,
    *,
    api_url: str = DEFAULT_LINEAR_API_URL,
) -> Mapping[str, Any]:
    """Send the Linear GraphQL mutation for the title update."""

    mutation = """
    mutation UpdateIssueTitle($issueId: String!, $title: String!) {
      issueUpdate(id: $issueId, input: { title: $title }) {
        success
        issue {
          id
          title
        }
      }
    }
    """
    body = json.dumps(
        {
            "query": mutation,
            "variables": {"issueId": update.issue_id, "title": update.new_title},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "User-Agent": "cursor-linear-research-title/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Linear API request failed: HTTP {error.code}: {error_body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Linear API request failed: {error.reason}") from error

    result = json.loads(response_body)
    if result.get("errors"):
        raise RuntimeError(f"Linear API returned errors: {result['errors']}")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Prefix Linear issue titles with "Cursor researching" on To Research transitions.'
    )
    parser.add_argument("--payload-file", help="Path to a JSON trigger payload.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the update that would be sent without calling Linear.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = read_payload(args)
    update = title_update_for_payload(payload)

    if update is None:
        print("No title update required.")
        return 0

    if args.dry_run:
        print(
            json.dumps(
                {
                    "issueId": update.issue_id,
                    "oldTitle": update.old_title,
                    "newTitle": update.new_title,
                },
                sort_keys=True,
            )
        )
        return 0

    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        raise ValueError("LINEAR_API_KEY is required to update Linear issue titles.")

    api_url = os.environ.get("LINEAR_API_URL", DEFAULT_LINEAR_API_URL)
    update_linear_issue_title(update, api_key, api_url=api_url)
    print(f"Updated {update.issue_id}: {update.new_title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
