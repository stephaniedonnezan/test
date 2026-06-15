import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4899",
                "title": "If the trading site is based in Germany or Spain",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4899",
                "title": "Cursor researching: If the trading site is based in Germany or Spain",
            },
        )

    def test_ignores_status_changed_payload_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Blocked",
                "id": "POI-4899",
                "title": "If the trading site is based in Germany or Spain",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_payload(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4899",
                "title": "If the trading site is based in Germany or Spain",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To Research",
                "id": "POI-4899",
                "title": "cursor researching: If the trading site is based in Germany or Spain",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_variants(self):
        for status in ("to_research", "to-research", "toResearch", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": status,
                        "id": "POI-4899",
                        "title": "UBA input compliance",
                    }
                }

                self.assertEqual(
                    build_issue_title_update(event),
                    {
                        "action": "update_issue_title",
                        "issueId": "POI-4899",
                        "title": "Cursor researching: UBA input compliance",
                    },
                )

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4899",
                    "title": "UBA input compliance",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4899",
                "title": "Cursor researching: UBA input compliance",
            },
        )

    def test_requires_status_field_for_generic_update(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4899",
                    "title": "UBA input compliance",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_target_status_from_change_payload(self):
        event = {
            "action": "Issue Updated",
            "changes": {"state": {"from": {"name": "Todo"}, "to": {"name": "To Research"}}},
            "data": {
                "issue": {
                    "identifier": "POI-4899",
                    "title": "UBA input compliance",
                    "state": {"name": "Todo"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4899",
                "title": "Cursor researching: UBA input compliance",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "UBA input compliance",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "POI-4899",
                    }
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4899",
                "title": "UBA input compliance",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4899",
                "title": "Cursor researching: UBA input compliance",
            },
        )


if __name__ == "__main__":
    unittest.main()
