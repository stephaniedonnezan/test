#!/usr/bin/env python3
"""Update Linear issue titles when issues move to the research status.

The script accepts a Linear/Cursor automation webhook payload as JSON on stdin
or from a file path. If the payload represents an issue status change into
"to research", it prefixes the issue title with "Cursor researching".
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


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"


@dataclass(frozen=True)
class IssueEvent:
    issue_id: str
    title: str
    new_status: str | None
    is_status_change: bool


@dataclass(frozen=True)
class TitleUpdate:
    issue_id: str
    current_title: str
    new_title: str
    new_status: str


class LinearApiError(RuntimeError):
    """Raised when Linear rejects the GraphQL request."""


def normalize_text(value: Any) -> str:
    return " ".join(str(value).strip().lower().split())


def has_research_prefix(title: str) -> bool:
    return normalize_text(title).startswith(normalize_text(TITLE_PREFIX))


def add_research_prefix(title: str) -> str:
    stripped_title = title.strip()
    if has_research_prefix(stripped_title):
        return stripped_title
    if not stripped_title:
        return TITLE_PREFIX
    return f"{TITLE_PREFIX}: {stripped_title}"


def read_payload(payload_file: str | None) -> Mapping[str, Any]:
    if payload_file:
        with open(payload_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise ValueError("Webhook payload must be a JSON object")
    return payload


def build_title_update(payload: Mapping[str, Any]) -> TitleUpdate | None:
    event = extract_issue_event(payload)
    if event is None:
        return None

    if not event.is_status_change:
        return None

    if normalize_text(event.new_status) != TARGET_STATUS:
        return None

    new_title = add_research_prefix(event.title)
    if new_title == event.title.strip():
        return None

    return TitleUpdate(
        issue_id=event.issue_id,
        current_title=event.title,
        new_title=new_title,
        new_status=event.new_status or "",
    )


def extract_issue_event(payload: Mapping[str, Any]) -> IssueEvent | None:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return extract_cursor_trigger_event(trigger_context)

    return extract_linear_webhook_event(payload)


def extract_cursor_trigger_event(trigger_context: Mapping[str, Any]) -> IssueEvent | None:
    issue_id = first_string(
        trigger_context,
        "linearId",
        "issueId",
        "identifier",
        "id",
    )
    title = first_string(trigger_context, "title")
    new_status = first_string(trigger_context, "newStatus", "status")
    trigger = first_string(trigger_context, "trigger", "event")

    if not issue_id or title is None:
        return None

    return IssueEvent(
        issue_id=issue_id,
        title=title,
        new_status=new_status,
        is_status_change=is_status_change_name(trigger),
    )


def extract_linear_webhook_event(payload: Mapping[str, Any]) -> IssueEvent | None:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        return None

    issue_id = first_string(data, "id", "identifier")
    title = first_string(data, "title")
    new_status = nested_string(data, ("state", "name")) or first_string(
        data,
        "status",
        "stateName",
    )

    if not issue_id or title is None:
        return None

    return IssueEvent(
        issue_id=issue_id,
        title=title,
        new_status=new_status,
        is_status_change=is_linear_status_change(payload),
    )


def first_string(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            return value
    return None


def nested_string(mapping: Mapping[str, Any], path: tuple[str, ...]) -> str | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None


def is_status_change_name(value: str | None) -> bool:
    normalized = normalize_text(value).replace("-", "_").replace(" ", "_")
    return normalized in {"status_changed", "status_change"}


def is_linear_status_change(payload: Mapping[str, Any]) -> bool:
    if is_status_change_name(first_string(payload, "trigger", "event", "action")):
        return True

    if normalize_text(payload.get("action")) != "update":
        return False

    updated_from = payload.get("updatedFrom")
    if not isinstance(updated_from, Mapping):
        return False

    return any(key in updated_from for key in ("stateId", "state", "stateName", "status"))


class LinearClient:
    def __init__(
        self,
        api_key: str,
        endpoint: str = LINEAR_GRAPHQL_URL,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint

    def update_issue_title(self, issue_id: str, title: str) -> None:
        query = """
        mutation UpdateIssueTitle($id: String!, $title: String!) {
          issueUpdate(id: $id, input: { title: $title }) {
            success
            issue {
              id
              identifier
              title
            }
          }
        }
        """
        response = self.execute(query, {"id": issue_id, "title": title})
        issue_update = response.get("issueUpdate")
        if not isinstance(issue_update, Mapping) or not issue_update.get("success"):
            raise LinearApiError("Linear did not confirm the issue title update")

    def execute(self, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                response_body = response.read()
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise LinearApiError(
                f"Linear API request failed with HTTP {error.code}: {details}"
            ) from error
        except urllib.error.URLError as error:
            raise LinearApiError(f"Linear API request failed: {error.reason}") from error

        decoded = json.loads(response_body)
        if not isinstance(decoded, Mapping):
            raise LinearApiError("Linear API returned a non-object response")
        if decoded.get("errors"):
            raise LinearApiError(f"Linear API returned errors: {decoded['errors']}")

        data = decoded.get("data")
        if not isinstance(data, Mapping):
            raise LinearApiError("Linear API response did not include data")
        return data


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prefix Linear issue titles with 'Cursor researching' when a status "
            "change moves the issue to 'to research'."
        )
    )
    parser.add_argument(
        "--payload-file",
        help="Path to a JSON webhook payload. Reads stdin when omitted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned update without calling the Linear API.",
    )
    parser.add_argument(
        "--api-key-env",
        default="LINEAR_API_KEY",
        help="Environment variable containing the Linear API key.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload = read_payload(args.payload_file)
    update = build_title_update(payload)

    if update is None:
        print("No Linear title update needed.")
        return 0

    print(
        "Linear issue "
        f"{update.issue_id} moved to {update.new_status!r}; "
        f"title will become {update.new_title!r}."
    )

    if args.dry_run:
        return 0

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise ValueError(f"Missing Linear API key in ${args.api_key_env}")

    LinearClient(api_key).update_issue_title(update.issue_id, update.new_title)
    print("Linear issue title updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
