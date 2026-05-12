import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_automation_payload_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4369",
                "title": "Rename and label Mass Balance canvas columns",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4369",
                "title": "Cursor researching: Rename and label Mass Balance canvas columns",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4369",
                "title": "Rename and label Mass Balance canvas columns",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4369",
                "title": "Rename and label Mass Balance canvas columns",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4369",
                "title": "cursor researching: Rename and label Mass Balance canvas columns",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4369",
                    "title": "Rename and label Mass Balance canvas columns",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4369",
                "title": "Cursor researching: Rename and label Mass Balance canvas columns",
            },
        )

    def test_rejects_issue_updates_without_status_field_changes(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4369",
                    "title": "Rename and label Mass Balance canvas columns",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_separators_and_camel_case_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "new_status": "to-research",
                "issueId": " POI-4369 ",
                "title": " Rename and label Mass Balance canvas columns ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4369",
                "title": "Cursor researching: Rename and label Mass Balance canvas columns",
            },
        )

    def test_requires_issue_identifier_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "id": "",
                        "title": "Rename and label Mass Balance canvas columns",
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
                        "id": "POI-4369",
                        "title": " ",
                    }
                }
            )
        )

    def test_cli_prints_json_update(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4369",
                "title": "Rename and label Mass Balance canvas columns",
            }
        }

        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4369",
                "title": "Cursor researching: Rename and label Mass Balance canvas columns",
            },
        )


if __name__ == "__main__":
    unittest.main()
