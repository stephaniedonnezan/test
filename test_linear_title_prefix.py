import unittest

from linear_title_prefix import build_issue_title_update, has_researching_prefix


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4340",
                "title": "Prevent delivery from being edited",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4340",
                "title": "Cursor researching: Prevent delivery from being edited",
            },
        )

    def test_accepts_flat_payload_and_normalized_status_names(self):
        event = {
            "trigger": "STATUS CHANGED",
            "newStatus": "to_research",
            "id": "POI-1",
            "title": "Review certificate ingestion",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Review certificate ingestion",
            },
        )

    def test_uses_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "status": "to research",
                "id": "POI-2",
                "title": "Investigate emissions calculation",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Investigate emissions calculation",
            },
        )

    def test_ignores_unrelated_statuses_and_triggers(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "In Review",
                        "id": "POI-3",
                        "title": "Research mass balance",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "comment_created",
                        "newStatus": "to research",
                        "id": "POI-4",
                        "title": "Research mass balance",
                    }
                }
            )
        )

    def test_does_not_duplicate_existing_researching_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "Cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Missing issue id",
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
                        "id": "POI-6",
                    }
                }
            )
        )


class HasResearchingPrefixTest(unittest.TestCase):
    def test_detects_prefix_case_insensitively_at_title_start(self):
        self.assertTrue(has_researching_prefix("cursor researching: Existing title"))
        self.assertTrue(has_researching_prefix("  CURSOR RESEARCHING - Existing title"))
        self.assertFalse(has_researching_prefix("Existing title Cursor researching"))


if __name__ == "__main__":
    unittest.main()
