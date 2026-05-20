import unittest

from linear_issue_title import (
    TITLE_PREFIX,
    normalize_status,
    title_for_status_change,
    title_with_research_prefix,
)


class LinearIssueTitleTest(unittest.TestCase):
    def test_normalize_status_collapses_case_and_whitespace(self):
        self.assertEqual(normalize_status("  To   Research "), "to research")

    def test_title_with_research_prefix_adds_prefix(self):
        self.assertEqual(
            title_with_research_prefix("Cleanup service"),
            f"{TITLE_PREFIX}: Cleanup service",
        )

    def test_title_with_research_prefix_is_idempotent(self):
        self.assertEqual(
            title_with_research_prefix("Cursor researching: Cleanup service"),
            "Cursor researching: Cleanup service",
        )

    def test_status_change_to_research_returns_prefixed_title(self):
        payload = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Cleanup service",
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching: Cleanup service",
        )

    def test_non_issue_payload_is_ignored(self):
        self.assertIsNone(
            title_for_status_change(
                {
                    "webhookType": "comment",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Cleanup service",
                }
            )
        )

    def test_other_status_is_ignored(self):
        self.assertIsNone(
            title_for_status_change(
                {
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "In Progress",
                    "title": "Cleanup service",
                }
            )
        )

    def test_missing_title_is_ignored(self):
        self.assertIsNone(
            title_for_status_change(
                {
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
