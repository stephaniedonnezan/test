#!/usr/bin/env python3
"""Update Linear issue titles when issues move to the research workflow state."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


LINEAR_API_URL = "https://api.linear.app/graphql"
RESEARCH_STATUS = "to research"
RESEARCH_MARKER = "Cursor researching"


class PayloadError(ValueError):
    """Raised when the webhook payload does not contain enough issue data."""


@dataclass(frozen=True)
class IssueEvent:
    issue_id: str
    title: str
    status: str


def normalize_status(status: str | None) -> str:
    """Normalize status labels so webhook casing and spacing differences are harmless."""
    return " ".join((status or "").strip().casefold().split())


def should_update_title(status: str | None, title: str | None) -> bool:
    """Return true only for research transitions that do not already carry the marker."""
    if normalize_status(status) != RESEARCH_STATUS:
        return False
    return RESEARCH_MARKER.casefold() not in (title or "").casefold()


def title_with_research_marker(title: str) -> str:
    """Add the Cursor research marker while preserving the issue's existing title text."""
    clean_title = title.strip()
    if RESEARCH_MARKER.casefold() in clean_title.casefold():
        return clean_title

    if clean_title.startswith("[]"):
        remainder = clean_title[2:].strip()
        return f"[{RESEARCH_MARKER}] {remainder}" if remainder else f"[{RESEARCH_MARKER}]"

    return f"[{RESEARCH_MARKER}] {clean_title}" if clean_title else f"[{RESEARCH_MARKER}]"


def extract_issue_event(payload: dict[str, Any]) -> IssueEvent:
    """Extract issue data from Cursor Automation or native Linear webhook payloads."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        issue_id = trigger_context.get("id") or trigger_context.get("identifier")
        title = trigger_context.get("title")
        status = trigger_context.get("newStatus") or trigger_context.get("status")
        if issue_id and title is not None and status:
            return IssueEvent(str(issue_id), str(title), str(status))

    data = payload.get("data")
    if isinstance(data, dict):
        state = data.get("state")
        issue_id = data.get("id") or data.get("identifier")
        title = data.get("title")
        status = data.get("stateName")
        if isinstance(state, dict):
            status = status or state.get("name")
        if issue_id and title is not None and status:
            return IssueEvent(str(issue_id), str(title), str(status))

    raise PayloadError("payload must include issue id, title, and status")


def update_linear_issue_title(
    issue_id: str,
    title: str,
    *,
    api_key: str,
    api_url: str = LINEAR_API_URL,
) -> dict[str, Any]:
    """Update a Linear issue title with Linear's GraphQL API."""
    issue_query = """
    query IssueForTitleUpdate($id: String!) {
      issue(id: $id) {
        id
      }
    }
    """
    mutation = """
    mutation UpdateIssueTitle($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) {
        success
        issue {
          id
          identifier
          title
        }
      }
    }
    """

    issue_data = linear_graphql(
        issue_query,
        {"id": issue_id},
        api_key=api_key,
        api_url=api_url,
    )
    resolved_issue_id = issue_data.get("issue", {}).get("id")
    if not resolved_issue_id:
        raise RuntimeError(f"Linear issue not found: {issue_id}")

    update_data = linear_graphql(
        mutation,
        {"id": resolved_issue_id, "input": {"title": title}},
        api_key=api_key,
        api_url=api_url,
    )
    update_result = update_data.get("issueUpdate", {})
    if not update_result.get("success"):
        raise RuntimeError(f"Linear API did not confirm title update: {update_data}")

    return update_result


def linear_graphql(
    query: str,
    variables: dict[str, Any],
    *,
    api_key: str,
    api_url: str,
) -> dict[str, Any]:
    """Run a Linear GraphQL request and return the response data."""
    body = json.dumps(
        {
            "query": query,
            "variables": variables,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=body,
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        response_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Linear API returned HTTP {error.code}: {response_body}") from error

    result = json.loads(response_body)
    if result.get("errors"):
        raise RuntimeError(f"Linear API returned errors: {result['errors']}")

    return result.get("data", {})


def load_payload() -> dict[str, Any]:
    """Load a webhook payload from stdin or AUTOMATION_TRIGGER_INFO."""
    stdin_payload = sys.stdin.read().strip()
    if stdin_payload:
        return json.loads(stdin_payload)

    env_payload = os.environ.get("AUTOMATION_TRIGGER_INFO")
    if env_payload:
        return json.loads(env_payload)

    raise PayloadError("provide webhook JSON on stdin or in AUTOMATION_TRIGGER_INFO")


def main() -> int:
    event = extract_issue_event(load_payload())
    if not should_update_title(event.status, event.title):
        print("No title update needed.")
        return 0

    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        raise RuntimeError("LINEAR_API_KEY is required to update Linear issue titles")

    new_title = title_with_research_marker(event.title)
    update_linear_issue_title(event.issue_id, new_title, api_key=api_key)
    print(f"Updated {event.issue_id} title to: {new_title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
