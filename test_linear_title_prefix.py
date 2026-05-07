import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2664",
                "title": "Unhandled onboarding rejection",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2664",
                "title": "Cursor researching: Unhandled onboarding rejection",
            },
        )

    def test_skips_status_changes_to_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-2664",
                "title": "Unhandled onboarding rejection",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-2664",
                "title": "Unhandled onboarding rejection",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_titles_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "To_Research",
                "id": "POI-2664",
                "title": "cursor researching: Unhandled onboarding rejection",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_linear_data_issue_shape_with_state_name(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-2664",
                    "title": "Unhandled onboarding rejection",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2664",
                "title": "Cursor researching: Unhandled onboarding rejection",
            },
        )

    def test_outer_trigger_context_overrides_nested_issue_state(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to-research",
                "data": {
                    "issue": {
                        "id": "POI-2664",
                        "title": "Unhandled onboarding rejection",
                        "state": {"name": "DEV"},
                    }
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2664",
                "title": "Cursor researching: Unhandled onboarding rejection",
            },
        )

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status changed",
            "status": "toResearch",
            "issueId": "POI-2664",
            "title": "  Unhandled onboarding rejection  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2664",
                "title": "Cursor researching: Unhandled onboarding rejection",
            },
        )

    def test_skips_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Unhandled onboarding rejection",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2664",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_blank_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2664",
            "title": "   ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
