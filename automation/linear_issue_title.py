#!/usr/bin/env python3
"""Update Linear issue titles when status transitions to "to research"."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
RESEARCH_PREFIX = "Cursor researching"
TITLE_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)
IDENTIFIER_PATTERN = re.compile(r"^(?P<team>[A-Za-z]+)-(?P<number>\d+)$")


class LinearApiError(RuntimeError):
    """Raised when Linear API requests fail."""


@dataclass
class IssueUpdateDecision:
    """Result for title update planning."""

    should_update: bool
    identifier: str
    current_title: str
    new_title: str


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalize_status(value: str) -> str:
    return _normalize_whitespace(value.strip().lower())


def extract_trigger_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Return trigger context from Cursor automation wrappers or raw payloads."""
    if isinstance(payload.get("triggerContext"), dict):
        return payload["triggerContext"]
    return payload


def should_prefix_title(context: dict[str, Any]) -> bool:
    """Whether this event should trigger research title prefixing."""
    if context.get("webhookType") != "issue":
        return False
    if context.get("trigger") != "status_changed":
        return False
    return _normalize_status(str(context.get("newStatus", ""))) == "to research"


def build_prefixed_title(current_title: str) -> str:
    """Create target title while preventing duplicate prefixes."""
    compact_title = current_title.strip()
    if TITLE_PATTERN.match(compact_title):
        return compact_title
    if not compact_title:
        return RESEARCH_PREFIX
    return f"{RESEARCH_PREFIX} - {compact_title}"


def plan_title_update(payload: dict[str, Any]) -> IssueUpdateDecision:
    """Compute whether an issue title needs updating for this webhook payload."""
    context = extract_trigger_context(payload)
    identifier = str(context.get("id", "")).strip()
    current_title = str(context.get("title", "")).strip()

    if not should_prefix_title(context) or not identifier:
        return IssueUpdateDecision(
            should_update=False,
            identifier=identifier,
            current_title=current_title,
            new_title=current_title,
        )

    new_title = build_prefixed_title(current_title)
    return IssueUpdateDecision(
        should_update=new_title != current_title,
        identifier=identifier,
        current_title=current_title,
        new_title=new_title,
    )


class LinearClient:
    """Minimal Linear GraphQL client."""

    def __init__(self, api_key: str, graphql_url: str = LINEAR_GRAPHQL_URL) -> None:
        self.api_key = api_key
        self.graphql_url = graphql_url

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        request_payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            self.graphql_url,
            data=request_payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": self.api_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise LinearApiError(f"Linear API HTTP error {exc.code}: {message}") from exc
        except urllib.error.URLError as exc:
            raise LinearApiError(f"Linear API request failed: {exc.reason}") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LinearApiError(f"Invalid JSON response from Linear API: {body}") from exc

        if data.get("errors"):
            raise LinearApiError(f"Linear API GraphQL errors: {data['errors']}")
        return data.get("data", {})

    def issue_id_for_identifier(self, identifier: str) -> str:
        """Resolve issue database id from human-readable identifier when possible."""
        match = IDENTIFIER_PATTERN.match(identifier)
        if not match:
            return identifier

        query = """
        query IssueByNumber($teamKey: String!, $number: Float!) {
          issueByNumber(teamKey: $teamKey, number: $number) {
            id
          }
        }
        """
        data = self.graphql(
            query=query,
            variables={
                "teamKey": match.group("team"),
                "number": float(match.group("number")),
            },
        )
        issue = data.get("issueByNumber")
        if not issue or not issue.get("id"):
            raise LinearApiError(f"Could not resolve issue id for identifier {identifier}")
        return str(issue["id"])

    def update_issue_title(self, issue_id: str, title: str) -> bool:
        mutation = """
        mutation UpdateIssueTitle($id: String!, $title: String!) {
          issueUpdate(id: $id, input: { title: $title }) {
            success
          }
        }
        """
        data = self.graphql(
            query=mutation,
            variables={"id": issue_id, "title": title},
        )
        result = data.get("issueUpdate") or {}
        return bool(result.get("success"))


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as infile:
            return json.load(infile)
    if args.payload_json:
        return json.loads(args.payload_json)
    if not sys.stdin.isatty():
        return json.load(sys.stdin)
    raise ValueError("No payload source provided. Use --payload-file, --payload-json, or stdin.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-file", help="Path to payload JSON file.")
    parser.add_argument("--payload-json", help="Raw payload JSON string.")
    parser.add_argument("--dry-run", action="store_true", help="Print update plan without API call.")
    args = parser.parse_args()

    try:
        payload = _load_payload(args)
        decision = plan_title_update(payload)
    except Exception as exc:  # broad because malformed automation payloads are common
        print(f"Failed to process payload: {exc}", file=sys.stderr)
        return 2

    if not decision.should_update:
        print("No title update required.")
        return 0

    print(f"Planned title update for {decision.identifier}: {decision.new_title}")
    if args.dry_run:
        return 0

    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("LINEAR_API_KEY is required to update Linear issues.", file=sys.stderr)
        return 2

    client = LinearClient(api_key=api_key)
    try:
        issue_id = client.issue_id_for_identifier(decision.identifier)
        updated = client.update_issue_title(issue_id=issue_id, title=decision.new_title)
    except LinearApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not updated:
        print("Linear did not confirm title update success.", file=sys.stderr)
        return 1

    print("Issue title updated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
