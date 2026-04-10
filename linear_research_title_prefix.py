#!/usr/bin/env python3
"""Prefix Linear issue titles when status changes to "to research"."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

LINEAR_API_URL = "https://api.linear.app/graphql"
DEFAULT_PREFIX = "Cursor researching"
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z]+-\d+$")


def normalize_text(value: str | None) -> str:
    """Normalize optional text for case-insensitive comparisons."""
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())


def should_prefix_for_status(status: str | None) -> bool:
    """Return True only for the "to research" status."""
    return normalize_text(status) == "to research"


def build_prefixed_title(title: str, prefix: str = DEFAULT_PREFIX) -> tuple[str, bool]:
    """Return prefixed title and whether a change was needed."""
    cleaned_title = title.strip()
    if cleaned_title.lower().startswith(prefix.lower()):
        return title, False
    return f"{prefix}: {cleaned_title}", True


def extract_identifier(trigger_context: dict[str, Any]) -> str | None:
    """Extract a Linear issue identifier from id or issue URL."""
    raw_id = str(trigger_context.get("id", "")).strip()
    if IDENTIFIER_PATTERN.match(raw_id):
        return raw_id.upper()

    url = str(trigger_context.get("url", "")).strip()
    # Example URL: https://linear.app/team/issue/POI-4050/some-slug
    marker = "/issue/"
    if marker not in url:
        return None
    tail = url.split(marker, 1)[1]
    identifier = tail.split("/", 1)[0].strip()
    if IDENTIFIER_PATTERN.match(identifier):
        return identifier.upper()
    return None


def linear_graphql_request(
    query: str,
    variables: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    """Send one GraphQL request to Linear and return parsed data."""
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": api_key,
    }
    request = urllib.request.Request(LINEAR_API_URL, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Linear API HTTP error {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Unable to reach Linear API: {exc.reason}") from exc

    parsed = json.loads(body)
    if parsed.get("errors"):
        raise RuntimeError(f"Linear GraphQL error: {parsed['errors']}")
    return parsed.get("data", {})


def fetch_issue(
    issue_id: str | None,
    issue_identifier: str | None,
    api_key: str,
    graphql_request: Callable[[str, dict[str, Any], str], dict[str, Any]] = linear_graphql_request,
) -> dict[str, str]:
    """Resolve the issue by id first, then identifier search fallback."""
    if issue_id:
        by_id_query = """
        query IssueById($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
          }
        }
        """
        try:
            data = graphql_request(by_id_query, {"id": issue_id}, api_key)
            issue = data.get("issue")
            if issue:
                return issue
        except RuntimeError:
            # Some trigger ids are identifiers (e.g. POI-1234), not UUIDs.
            # In that case, fall back to issue search by identifier.
            pass

    if issue_identifier:
        search_query = """
        query IssueSearch($query: String!) {
          issueSearch(query: $query, first: 10) {
            nodes {
              id
              identifier
              title
            }
          }
        }
        """
        data = graphql_request(search_query, {"query": issue_identifier}, api_key)
        nodes = data.get("issueSearch", {}).get("nodes", [])
        for node in nodes:
            if normalize_text(node.get("identifier")) == normalize_text(issue_identifier):
                return node

    raise RuntimeError("Could not resolve issue from trigger payload.")


def update_issue_title(
    linear_issue_id: str,
    title: str,
    api_key: str,
    graphql_request: Callable[[str, dict[str, Any], str], dict[str, Any]] = linear_graphql_request,
) -> dict[str, Any]:
    """Update a Linear issue title by UUID."""
    mutation = """
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
    data = graphql_request(mutation, {"id": linear_issue_id, "title": title}, api_key)
    result = data.get("issueUpdate", {})
    if not result.get("success"):
        raise RuntimeError(f"Linear refused title update for issue id {linear_issue_id}.")
    return result.get("issue", {})


def process_trigger_payload(
    payload: dict[str, Any],
    api_key: str,
    prefix: str = DEFAULT_PREFIX,
    graphql_request: Callable[[str, dict[str, Any], str], dict[str, Any]] = linear_graphql_request,
) -> dict[str, Any]:
    """Handle one automation payload and update title when needed."""
    trigger_context = payload.get("triggerContext", payload)
    trigger = normalize_text(trigger_context.get("trigger"))
    status = trigger_context.get("newStatus") or trigger_context.get("status")

    if trigger and trigger != "status_changed":
        return {"updated": False, "reason": "trigger was not status_changed"}
    if not should_prefix_for_status(status):
        return {"updated": False, "reason": "status was not to research"}

    issue_id = str(trigger_context.get("id", "")).strip() or None
    issue_identifier = extract_identifier(trigger_context)
    issue = fetch_issue(issue_id, issue_identifier, api_key, graphql_request)

    new_title, changed = build_prefixed_title(issue["title"], prefix=prefix)
    if not changed:
        return {
            "updated": False,
            "reason": "title already prefixed",
            "issueIdentifier": issue.get("identifier"),
            "title": issue["title"],
        }

    updated_issue = update_issue_title(issue["id"], new_title, api_key, graphql_request)
    return {
        "updated": True,
        "issueIdentifier": updated_issue.get("identifier"),
        "title": updated_issue.get("title", new_title),
    }


def _read_payload_from_stdin() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        raise RuntimeError("No JSON payload supplied on stdin.")
    return json.loads(raw)


def main() -> int:
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        raise RuntimeError("LINEAR_API_KEY environment variable is required.")

    payload = _read_payload_from_stdin()
    result = process_trigger_payload(payload, api_key=api_key)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
