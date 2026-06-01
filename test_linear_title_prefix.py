import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_to_research_status_change(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3948",
                "title": "Mass Balance Export of production sites",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3948",
                "title": "Cursor researching: Mass Balance Export of production sites",
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        result = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "status": "To Research",
                "issueId": "POI-1",
                "title": "Investigate importer",
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Investigate importer")

    def test_accepts_separator_and_case_variations(self):
        result = build_issue_title_update(
            {
                "trigger": "STATUS-CHANGED",
                "new_status": "TO_RESEARCH",
                "identifier": "POI-2",
                "title": "  Normalize statuses  ",
            }
        )

        self.assertEqual(result["issueId"], "POI-2")
        self.assertEqual(result["title"], "Cursor researching: Normalize statuses")

    def test_skips_non_status_change_trigger(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Do not update",
            }
        )

        self.assertIsNone(result)

    def test_skips_other_status(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4",
                "title": "Already done",
            }
        )

        self.assertIsNone(result)

    def test_skips_title_that_already_has_prefix(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "cursor researching: Existing prefix",
            }
        )

        self.assertIsNone(result)

    def test_accepts_nested_automation_trigger_context(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-6",
                    "title": "Nested trigger context",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Nested trigger context")

    def test_accepts_linear_issue_update_when_status_field_changed(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "id": "POI-7",
                    "title": "Nested Linear issue",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Nested Linear issue")

    def test_skips_linear_issue_update_when_status_field_not_changed(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["description"],
                "data": {
                    "id": "POI-8",
                    "title": "Description changed",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_skips_missing_required_values(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-9",
                }
            )
        )

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-10",
            "title": "CLI payload",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: CLI payload",
            },
        )


if __name__ == "__main__":
    unittest.main()
