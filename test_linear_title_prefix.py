import unittest

from linear_title_prefix import CURSOR_RESEARCHING_PREFIX, build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4463",
                "title": "Feedback to user when LPH upload fails",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4463",
                "title": (
                    f"{CURSOR_RESEARCHING_PREFIX}: "
                    "Feedback to user when LPH upload fails"
                ),
            },
        )

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4463",
            "title": "Investigate LPH upload failures",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4463",
                "title": (
                    f"{CURSOR_RESEARCHING_PREFIX}: "
                    "Investigate LPH upload failures"
                ),
            },
        )

    def test_normalizes_trigger_and_status_separators(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "newStatus": "to_research",
                "id": "POI-4463",
                "title": "Normalize values",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{CURSOR_RESEARCHING_PREFIX}: Normalize values",
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4463",
                "title": "Fallback status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{CURSOR_RESEARCHING_PREFIX}: Fallback status",
        )

    def test_does_not_prefix_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4463",
                "title": "Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_prefix_for_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-4463",
                "title": "Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4463",
                "title": "Cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4463",
                "title": "cursor Researching - Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4463",
                "title": "  Existing title  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{CURSOR_RESEARCHING_PREFIX}: Existing title",
        )

    def test_requires_issue_id_and_title(self):
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Existing title",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4463",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))


if __name__ == "__main__":
    unittest.main()
