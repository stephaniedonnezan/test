import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
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
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4542",
            "title": "Fix conversion constants",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4542",
                "title": "Cursor researching: Fix conversion constants",
            },
        )

    def test_accepts_issue_id_when_id_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "issueId": "POI-4542",
                "title": "Fix conversion constants",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4542",
                "title": "Cursor researching: Fix conversion constants",
            },
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4542",
                "title": "Fix conversion constants",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fix conversion constants",
        )

    def test_normalizes_trigger_and_status(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": " to-research ",
                "id": "POI-4542",
                "title": "Fix conversion constants",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fix conversion constants",
        )

    def test_returns_none_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4542",
                "title": "Fix conversion constants",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_other_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "Fix conversion constants",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_title_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "Cursor researching: Fix conversion constants",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "cursor researching - Fix conversion constants",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "  Fix conversion constants  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fix conversion constants",
        )

    def test_returns_none_without_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "To Research",
                        "title": "Fix conversion constants",
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
                        "id": "POI-4542",
                    }
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
