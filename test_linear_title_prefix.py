import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4530",
                "title": "UBA specific fields in Atmen",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4530",
                "title": "Cursor researching: UBA specific fields in Atmen",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4530",
            "title": "UBA specific fields in Atmen",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4530",
                "title": "Cursor researching: UBA specific fields in Atmen",
            },
        )

    def test_accepts_issue_id_fallback(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4530",
                "title": "UBA specific fields in Atmen",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4530",
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4530",
                "title": "UBA specific fields in Atmen",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA specific fields in Atmen",
        )

    def test_normalizes_status_separators(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": "to_research",
                "id": "POI-4530",
                "title": "UBA specific fields in Atmen",
            }
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_ignores_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4530",
                "title": "UBA specific fields in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4530",
                "title": "UBA specific fields in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4530",
                "title": "cursor Researching: UBA specific fields in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4530",
                "title": "  UBA specific fields in Atmen  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: UBA specific fields in Atmen",
        )

    def test_ignores_blank_titles(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4530",
                "title": "   ",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "UBA specific fields in Atmen",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
