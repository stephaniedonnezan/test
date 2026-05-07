import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4234",
                "title": "Link Issues/Alerts to actions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4234",
                "title": "Cursor researching: Link Issues/Alerts to actions",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Triage",
                "id": "POI-4234",
                "title": "Link Issues/Alerts to actions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4234",
                "title": "Link Issues/Alerts to actions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4234",
                "title": "cursor researching: Link Issues/Alerts to actions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_flat_payload_and_normalized_status(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4234",
            "title": "Link Issues/Alerts to actions",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4234",
                "title": "Cursor researching: Link Issues/Alerts to actions",
            },
        )

    def test_prefers_explicit_new_status_over_generic_status(self):
        event = {
            "newStatus": "To Research",
            "triggerContext": {
                "trigger": "status_changed",
                "status": "Triage",
                "id": "POI-4234",
                "title": "Link Issues/Alerts to actions",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4234",
                "title": "Cursor researching: Link Issues/Alerts to actions",
            },
        )

    def test_accepts_nested_linear_issue_payload(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4234",
                    "title": "Link Issues/Alerts to actions",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4234",
                "title": "Cursor researching: Link Issues/Alerts to actions",
            },
        )

    def test_ignores_issue_updated_without_status_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4234",
                    "title": "Link Issues/Alerts to actions",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Link Issues/Alerts to actions",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4234",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
