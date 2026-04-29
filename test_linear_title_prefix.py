import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4547",
                "title": "Add sustainability documents",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4547",
                "title": "Cursor researching: Add sustainability documents",
            },
        )

    def test_accepts_flat_event_payloads(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4547",
            "title": "Add sustainability documents",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add sustainability documents",
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4547",
                "title": "Add sustainability documents",
            }
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_accepts_issue_id_field(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4547",
                "title": "Add sustainability documents",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4547")

    def test_normalizes_status_case_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "newStatus": "To_Research",
                "id": "POI-4547",
                "title": "Add sustainability documents",
            }
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4547",
                "title": "  Add sustainability documents  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Add sustainability documents",
        )

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4547",
                "title": "Cursor researching: Add sustainability documents",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4547",
                "title": "cursor researching Add sustainability documents",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4547",
                "title": "Add sustainability documents",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-4547",
                "title": "Add sustainability documents",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Add sustainability documents",
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
                        "id": "POI-4547",
                    }
                }
            )
        )

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
