import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4562",
                "title": "distance_travelled_km is overwritten",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4562",
                "title": "Cursor researching: distance_travelled_km is overwritten",
            },
        )

    def test_accepts_flat_payload_shape(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-4562",
            "title": "Use provided distanceTravelled",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4562",
                "title": "Cursor researching: Use provided distanceTravelled",
            },
        )

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4562",
                "title": "Use provided distanceTravelled",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Use provided distanceTravelled",
        )

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "triggerContext": {
                "trigger": "Status-Changed",
                "newStatus": "TO_RESEARCH",
                "id": "POI-4562",
                "title": "Use provided distanceTravelled",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Use provided distanceTravelled",
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4562",
                "title": "Use provided distanceTravelled",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4562",
                "title": "Use provided distanceTravelled",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4562",
                "title": "cursor researching: Use provided distanceTravelled",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_and_issue_id_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "  POI-4562  ",
                "title": "  Use provided distanceTravelled  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4562",
                "title": "Cursor researching: Use provided distanceTravelled",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Use provided distanceTravelled",
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
                        "id": "POI-4562",
                        "title": "   ",
                    }
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
