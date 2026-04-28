import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4564",
                "title": "Inputs were set to 0",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4564",
                "title": "Cursor researching: Inputs were set to 0",
            },
        )

    def test_supports_flat_payloads(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4564",
            "title": "Inputs were set to 0",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4564",
                "title": "Cursor researching: Inputs were set to 0",
            },
        )

    def test_accepts_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4564",
                "title": "Inputs were set to 0",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Inputs were set to 0",
        )

    def test_normalizes_trigger_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "To-Research",
                "id": "POI-4564",
                "title": "Inputs were set to 0",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Inputs were set to 0",
        )

    def test_skips_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_updated",
                "newStatus": "to research",
                "id": "POI-4564",
                "title": "Inputs were set to 0",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4564",
                "title": "Inputs were set to 0",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_already_prefixed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4564",
                "title": "Cursor researching: Inputs were set to 0",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_already_prefixed_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4564",
                "title": "cursor researching inputs were set to 0",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4564",
                "title": "  Inputs were set to 0  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Inputs were set to 0",
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Inputs were set to 0",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4564",
                    }
                }
            )
        )

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
