import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "automationId": "automation-1",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4748",
                "title": (
                    "[Energy Allocation Migration] January 2025 showing "
                    "differently for the mass balance and for the energy "
                    "allocation"
                ),
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4748",
                "title": (
                    "Cursor researching: [Energy Allocation Migration] "
                    "January 2025 showing differently for the mass balance "
                    "and for the energy allocation"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4748",
            "title": "Investigate energy allocation setup",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4748",
            "title": "Investigate energy allocation setup",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4748",
            "title": "cursor researching: Investigate energy allocation setup",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_handles_nested_linear_issue_update_payloads(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4748",
                "title": "Investigate energy allocation setup",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate energy allocation setup",
            },
        )

    def test_accepts_case_and_separator_variants_for_status(self):
        event = {
            "trigger": "stateChanged",
            "newStatus": "to-research",
            "identifier": "POI-4748",
            "title": "Check import states",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4748",
                "title": "Cursor researching: Check import states",
            },
        )

    def test_uses_issue_nested_in_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issue": {
                    "id": "POI-4748",
                    "title": "Review automation payload",
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4748",
                "title": "Cursor researching: Review automation payload",
            },
        )

    def test_requires_status_field_for_generic_update_events(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "issue-uuid",
                "title": "Investigate energy allocation setup",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing issue id",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4748",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
