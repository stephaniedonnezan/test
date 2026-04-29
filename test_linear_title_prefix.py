import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4104",
                "title": "Include storage loss traceability on the MB export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4104",
                "title": "Cursor researching: Include storage loss traceability on the MB export",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "statusChanged",
            "status": "to_research",
            "issueId": "POI-4104",
            "title": "Trace storage losses",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4104",
                "title": "Cursor researching: Trace storage losses",
            },
        )

    def test_accepts_linear_action_name(self):
        event = {
            "action": "statusChanged",
            "data": {
                "state": {"name": "To Research"},
                "id": "POI-4104",
                "title": "Trace storage losses",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4104",
                "title": "Cursor researching: Trace storage losses",
            },
        )

    def test_accepts_trigger_outside_nested_data(self):
        event = {
            "trigger": "status_changed",
            "data": {
                "newStatus": "To Research",
                "issue": {
                    "id": "POI-4104",
                    "title": "Trace storage losses",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4104",
                "title": "Cursor researching: Trace storage losses",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Duplicate",
                "id": "POI-4104",
                "title": "Trace storage losses",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4104",
                "title": "Trace storage losses",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4104",
                "title": "Cursor researching: Trace storage losses",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_duplicate_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4104",
                "title": "cursor researching: Trace storage losses",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Trace storage losses",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4104",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))


if __name__ == "__main__":
    unittest.main()
