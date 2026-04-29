import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4573",
                "title": "Random stock overflow on Turn2X Jan 2026",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4573",
                "title": "Cursor researching: Random stock overflow on Turn2X Jan 2026",
            },
        )

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-123",
            "title": "Investigate export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate export",
            },
        )

    def test_accepts_nested_issue_data(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "data": {
                    "issueId": "POI-124",
                    "title": "Nested issue title",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-124",
                "title": "Cursor researching: Nested issue title",
            },
        )

    def test_outer_trigger_metadata_overrides_nested_data(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-125",
                "title": "Outer title",
                "data": {
                    "id": "POI-999",
                    "title": "Inner title",
                    "newStatus": "done",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-125",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_accepts_linear_action_status_changed(self):
        event = {
            "triggerContext": {
                "action": "statusChanged",
                "status": "to research",
                "id": "POI-126",
                "title": "Action payload",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-126",
                "title": "Cursor researching: Action payload",
            },
        )

    def test_accepts_state_name_as_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "state": {"name": "To Research"},
                "id": "POI-127",
                "title": "State status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-127",
                "title": "Cursor researching: State status",
            },
        )

    def test_normalizes_status_and_trigger_separators(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "new_status": "TO_RESEARCH",
                "id": "POI-128",
                "title": "Separator variations",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-128",
                "title": "Cursor researching: Separator variations",
            },
        )

    def test_ignores_non_status_changed_events(self):
        event = {
            "triggerContext": {
                "trigger": "created",
                "newStatus": "to research",
                "id": "POI-129",
                "title": "Created issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_statuses_other_than_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-130",
                "title": "Development issue",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-131",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-132",
                "title": "  Trim me  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-132",
                "title": "Cursor researching: Trim me",
            },
        )

    def test_ignores_invalid_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update([]))
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-133",
                    }
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
