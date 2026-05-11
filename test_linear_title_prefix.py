import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3175",
                "title": "Mass Balance re-opening follow up",
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-3175",
                "title": "Cursor researching: Mass Balance re-opening follow up",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        update = build_issue_title_update(
            {
                "trigger": "statusChanged",
                "new_status": "To-Research",
                "issueId": "POI-1",
                "title": "Check edge cases",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Check edge cases")

    def test_uses_status_when_new_status_is_absent(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "status": "To Research",
                "identifier": "POI-2",
                "title": "Fallback status",
            }
        )

        self.assertEqual(update["issueId"], "POI-2")

    def test_handles_nested_linear_issue_payload(self):
        update = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "issue": {
                        "id": "issue-uuid",
                        "title": "Nested payload",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Nested payload",
            },
        )

    def test_ignores_non_status_trigger(self):
        update = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Comment only",
            }
        )

        self.assertIsNone(update)

    def test_ignores_issue_update_without_status_field_change(self):
        update = build_issue_title_update(
            {
                "action": "Issue Updated",
                "updatedFields": ["title"],
                "id": "POI-4",
                "title": "Title only",
                "status": "To Research",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_research_status(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "id": "POI-5",
                "title": "Do not prefix",
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "cursor researching: Already marked",
            }
        )

        self.assertIsNone(update)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-7",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
                "title": "From stdin",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-8",
                "title": "Cursor researching: From stdin",
            },
        )


if __name__ == "__main__":
    unittest.main()
