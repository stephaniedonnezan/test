import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4509",
                "title": "Org user should be able to change audit dates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4509",
                "title": "Cursor researching: Org user should be able to change audit dates",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4509",
            "title": "Investigate audit dates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4509",
                "title": "Cursor researching: Investigate audit dates",
            },
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4509",
                "title": "Investigate audit dates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate audit dates",
        )

    def test_accepts_issue_id_field(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4509",
                "title": "Investigate audit dates",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4509")

    def test_normalizes_trigger_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": " TO-RESEARCH ",
                "id": "POI-4509",
                "title": "Investigate audit dates",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate audit dates",
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-4509",
                "title": "Investigate audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4509",
                "title": "Investigate audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4509",
                "title": "Cursor researching: Investigate audit dates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4509",
                "title": "cursor researching - Investigate audit dates",
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
                        "title": "Investigate audit dates",
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
                        "id": "POI-4509",
                    }
                }
            )
        )

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
