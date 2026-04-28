import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "Fix floating-point precision loss",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4542",
                "title": "Cursor researching: Fix floating-point precision loss",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status changed",
            "newStatus": "to_research",
            "id": "POI-4542",
            "title": "Fix precision",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fix precision",
        )

    def test_falls_back_to_status_when_new_status_missing(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "status": "to research",
                "id": "POI-4542",
                "title": "Fix precision",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fix precision",
        )

    def test_accepts_issue_id_alias(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4542",
                "title": "Fix precision",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4542")

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4542",
                "title": "  Fix precision  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fix precision",
        )

    def test_no_update_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4542",
                "title": "Fix precision",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_no_update_for_other_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "issue_updated",
                "newStatus": "to research",
                "id": "POI-4542",
                "title": "Fix precision",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_no_update_when_already_prefixed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4542",
                "title": "Cursor researching: Fix precision",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4542",
                "title": "cursor researching - Fix precision",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_no_update_without_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Fix precision",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_no_update_without_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4542",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
