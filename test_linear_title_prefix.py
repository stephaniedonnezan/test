import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_flat_status_changed_trigger(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5082",
                "title": "Bug: stoichemistry",
            }
        )

        self.assertEqual(
            action,
            {
                "action": "update_issue_title",
                "issueId": "POI-5082",
                "title": "Cursor researching: Bug: stoichemistry",
            },
        )

    def test_accepts_nested_linear_issue_update_payload(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "identifier": "POI-5082",
                        "title": "Bug: stoichemistry",
                        "state": {"name": "To Research"},
                    },
                },
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Bug: stoichemistry")
        self.assertEqual(action["issueId"], "POI-5082")

    def test_accepts_status_variants_case_and_separators(self):
        action = build_issue_title_update(
            {
                "webhookType": "statusChanged",
                "new_status": "TO_RESEARCH",
                "issueId": "POI-5082",
                "title": "Bug: stoichemistry",
            }
        )

        self.assertEqual(action["title"], "Cursor researching: Bug: stoichemistry")

    def test_ignores_non_research_status(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-5082",
                "title": "Bug: stoichemistry",
            }
        )

        self.assertIsNone(action)

    def test_ignores_non_status_update(self):
        action = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["title"],
                "status": "to research",
                "id": "POI-5082",
                "title": "Bug: stoichemistry",
            }
        )

        self.assertIsNone(action)

    def test_does_not_duplicate_existing_prefix(self):
        action = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5082",
                "title": "cursor researching: Bug: stoichemistry",
            }
        )

        self.assertEqual(action["title"], "cursor researching: Bug: stoichemistry")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Bug: stoichemistry",
                }
            )
        )

    def test_cli_prints_update_action(self):
        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "toResearch",
                        "id": "POI-5082",
                        "title": "Bug: stoichemistry",
                    }
                }
            ),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5082",
                "title": "Cursor researching: Bug: stoichemistry",
            },
        )


if __name__ == "__main__":
    unittest.main()
