import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4475",
                "title": "Custom LHV for methane plant for turn2x",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4475",
                "title": "Cursor researching: Custom LHV for methane plant for turn2x",
            },
        )

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4475",
            "title": "Investigate methane LHV",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4475",
                "title": "Cursor researching: Investigate methane LHV",
            },
        )

    def test_accepts_issue_id_key(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4475",
                "title": "Investigate methane LHV",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4475",
                "title": "Cursor researching: Investigate methane LHV",
            },
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4475",
                "title": "Investigate methane LHV",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate methane LHV",
        )

    def test_normalizes_trigger_and_status_separators(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "To-Research",
                "id": "POI-4475",
                "title": "Investigate methane LHV",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate methane LHV",
        )

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4475",
                "title": "  Investigate methane LHV  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate methane LHV",
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4475",
                "title": "Cursor researching: Investigate methane LHV",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4475",
                "title": "cursor Researching - Investigate methane LHV",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_events(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-4475",
                "title": "Investigate methane LHV",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4475",
                "title": "Investigate methane LHV",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate methane LHV",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4475",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
