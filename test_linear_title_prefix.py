import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_to_research_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5057",
                "title": "Redesign of Add Input",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5057",
                "title": "Cursor researching: Redesign of Add Input",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-5057",
                "title": "Redesign of Add Input",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5057",
                "title": "Redesign of Add Input",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5057",
                "title": "Cursor researching: Redesign of Add Input",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5057",
                "title": "cursor Researching - Redesign of Add Input",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-5057",
                "title": "Redesign of Add Input",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Redesign of Add Input",
        )

    def test_accepts_camel_case_status_name(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": "toResearch",
                "id": "POI-5057",
                "title": "Redesign of Add Input",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Redesign of Add Input",
        )

    def test_uses_status_fallback_when_new_status_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-5057",
                "title": "Redesign of Add Input",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5057")

    def test_handles_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "linear-uuid",
                "identifier": "POI-5057",
                "title": "Redesign of Add Input",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5057",
                "title": "Cursor researching: Redesign of Add Input",
            },
        )

    def test_handles_nested_issue_object(self):
        event = {
            "action": "Issue Updated",
            "changes": {"status": {"from": "Todo", "to": "To Research"}},
            "issue": {
                "issueId": "POI-5057",
                "title": "Redesign of Add Input",
            },
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5057")

    def test_ignores_generic_update_without_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["title"],
            "data": {
                "identifier": "POI-5057",
                "title": "Redesign of Add Input",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Redesign of Add Input",
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
                        "id": "POI-5057",
                    }
                }
            )
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": " POI-5057 ",
                "title": " Redesign of Add Input ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5057",
                "title": "Cursor researching: Redesign of Add Input",
            },
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5057",
                "title": "Redesign of Add Input",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5057",
                "title": "Cursor researching: Redesign of Add Input",
            },
        )


if __name__ == "__main__":
    unittest.main()
