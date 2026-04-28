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

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "status changed",
            "status": "to research",
            "issueId": "POI-4542",
            "title": "Investigate conversion constants",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4542",
                "title": "Cursor researching: Investigate conversion constants",
            },
        )

    def test_handles_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "newStatus": "  to-research  ",
                "id": "POI-4542",
                "title": "Normalize fields",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Normalize fields",
        )

    def test_uses_new_status_before_status_fallback(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "status": "Backlog",
                "id": "POI-4542",
                "title": "Use new status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Use new status",
        )

    def test_skips_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_updated",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "Do not prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-4542",
                "title": "Do not prefix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "cursor researching: Already prefixed",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Missing id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4542",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4542",
                "title": "  Trim this title  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trim this title",
        )


if __name__ == "__main__":
    unittest.main()
