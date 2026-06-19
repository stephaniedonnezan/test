import json
import subprocess
import sys
import unittest

from linear_issue_title import (
    build_title_update,
    normalize_status,
    title_with_research_marker,
)


class LinearIssueTitleTest(unittest.TestCase):
    def test_normalize_status_accepts_common_variants(self) -> None:
        self.assertEqual(normalize_status("To Research"), "to research")
        self.assertEqual(normalize_status(" to-research "), "to research")
        self.assertEqual(normalize_status("TO_RESEARCH"), "to research")

    def test_adds_cursor_researching_marker_for_to_research_status(self) -> None:
        self.assertEqual(
            title_with_research_marker("Trader: Add dispatch date sanity check", "to research"),
            "Cursor researching: Trader: Add dispatch date sanity check",
        )

    def test_leaves_other_status_titles_unchanged(self) -> None:
        self.assertEqual(
            title_with_research_marker("Trader: Add dispatch date sanity check", "QA"),
            "Trader: Add dispatch date sanity check",
        )

    def test_does_not_duplicate_existing_marker(self) -> None:
        title = "Cursor researching: Trader: Add dispatch date sanity check"
        self.assertEqual(title_with_research_marker(title, "to research"), title)

    def test_builds_update_for_linear_issue_status_change_to_research(self) -> None:
        self.assertEqual(
            build_title_update(
                {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4249",
                    "title": "Trader: Add dispatch date sanity check",
                }
            ),
            {
                "id": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )

    def test_ignores_non_matching_events(self) -> None:
        self.assertIsNone(
            build_title_update(
                {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-4249",
                    "title": "Trader: Add dispatch date sanity check",
                }
            )
        )

    def test_cli_outputs_update_payload(self) -> None:
        payload = {
            "triggerType": "linear",
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4249",
            "title": "Trader: Add dispatch date sanity check",
        }

        result = subprocess.run(
            [sys.executable, "linear_issue_title.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "id": "POI-4249",
                "title": "Cursor researching: Trader: Add dispatch date sanity check",
            },
        )


if __name__ == "__main__":
    unittest.main()
