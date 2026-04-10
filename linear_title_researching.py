#!/usr/bin/env python3
"""Update Linear issue titles when status changes to "to research"."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

LINEAR_API_URL = "https://api.linear.app/graphql"
TITLE_MARKER = "Cursor researching"


def _normalize_status(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().lower().split())


def should_mark_issue(payload: dict[str, Any]) -> bool:
    """Return True when this webhook means the issue entered to research."""
    trigger_context = payload.get("triggerContext", {}) if isinstance(payload, dict) else {}
    new_status = trigger_context.get("newStatus")
    return _normalize_status(new_status) == "to research"


def build_updated_title(title: str, marker: str = TITLE_MARKER) -> str:
    """Prefix marker to title once, preserving existing marker."""
    cleaned_title = title.strip()
    if cleaned_title.lower().startswith(marker.lower()):
        return cleaned_title
    return f"{marker} {cleaned_title}"


def _graphql_request(api_key: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        LINEAR_API_URL,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    result = json.loads(body)
    if result.get("errors"):
        raise RuntimeError(f"Linear GraphQL error: {result['errors']}")
    return result


def _extract_issue_identifier(payload: dict[str, Any]) -> str:
    trigger_context = payload.get("triggerContext", {}) if isinstance(payload, dict) else {}
    identifier = trigger_context.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("Could not read issue identifier from payload.triggerContext.id")
    return identifier.strip()


def _fetch_issue_by_identifier(api_key: str, identifier: str) -> dict[str, str] | None:
    query = """
    query FindIssueByIdentifier($identifier: String!) {
      issues(filter: { identifier: { eq: $identifier } }, first: 1) {
        nodes {
          id
          identifier
          title
        }
      }
    }
    """
    response = _graphql_request(api_key, query, {"identifier": identifier})
    nodes = response.get("data", {}).get("issues", {}).get("nodes", [])
    if not nodes:
        return None
    node = nodes[0]
    return {
        "id": node["id"],
        "identifier": node["identifier"],
        "title": node["title"],
    }


def _update_issue_title(api_key: str, issue_id: str, new_title: str) -> bool:
    mutation = """
    mutation UpdateIssueTitle($id: String!, $title: String!) {
      issueUpdate(id: $id, input: { title: $title }) {
        success
      }
    }
    """
    response = _graphql_request(api_key, mutation, {"id": issue_id, "title": new_title})
    return bool(response.get("data", {}).get("issueUpdate", {}).get("success"))


def run(payload: dict[str, Any], api_key: str) -> int:
    if not should_mark_issue(payload):
        print("Status is not 'to research'; no title update required.")
        return 0

    issue_identifier = _extract_issue_identifier(payload)
    issue = _fetch_issue_by_identifier(api_key, issue_identifier)
    if issue is None:
        print(f"Issue {issue_identifier} not found in Linear.")
        return 1

    new_title = build_updated_title(issue["title"])
    if new_title == issue["title"].strip():
        print(f"Issue {issue_identifier} already contains '{TITLE_MARKER}'.")
        return 0

    success = _update_issue_title(api_key, issue["id"], new_title)
    if not success:
        print(f"Failed to update title for issue {issue_identifier}.")
        return 1

    print(f"Updated issue {issue_identifier} title to: {new_title}")
    return 0


def _read_payload(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add 'Cursor researching' to Linear issue title when status changes to 'to research'."
    )
    parser.add_argument(
        "--payload",
        default=None,
        help="Path to a JSON payload file (if omitted, reads from stdin).",
    )
    args = parser.parse_args()

    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("Missing LINEAR_API_KEY environment variable.")
        return 1

    try:
        payload = _read_payload(args.payload)
        return run(payload, api_key)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid payload: {exc}")
        return 1
    except urllib.error.URLError as exc:
        print(f"Network error while contacting Linear: {exc}")
        return 1
    except RuntimeError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
