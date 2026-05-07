import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_change_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4595",
            "title": "Issue in Container Trips Excel export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4595",
                "title": "Cursor researching: Issue in Container Trips Excel export",
            },
        )

    def test_accepts_cursor_trigger_context_shape(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4595",
                "title": "Negative value in export",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4595",
                "title": "Cursor researching: Negative value in export",
            },
        )

    def test_accepts_nested_linear_issue_payload_shape(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4595",
                    "title": "Container trip export shows negative value",
                    "state": {"name": "toResearch"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4595",
                "title": "Cursor researching: Container trip export shows negative value",
            },
        )

    def test_outer_fields_override_nested_issue_fields(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-1111",
                "title": "Nested title",
            },
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4595",
            "title": "Outer title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4595",
                "title": "Cursor researching: Outer title",
            },
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4595",
            "title": "Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-4595",
            "title": "Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_status_separators_and_casing(self):
        for status in ("to_research", "To-Research", "toResearch", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-4595",
                    "title": "Issue title",
                }

                self.assertEqual(
                    build_issue_title_update(event),
                    {
                        "action": "update_issue_title",
                        "issueId": "POI-4595",
                        "title": "Cursor researching: Issue title",
                    },
                )

    def test_uses_status_when_new_status_is_missing(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "id": "POI-4595",
            "title": "Issue title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4595",
                "title": "Cursor researching: Issue title",
            },
        )

    def test_uses_issue_id_fallbacks(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issue_id": "POI-4595",
            "title": "Issue title",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4595",
                "title": "Cursor researching: Issue title",
            },
        )

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4595 ",
            "title": "  Issue title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4595",
                "title": "Cursor researching: Issue title",
            },
        )

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4595",
            "title": "Cursor researching: Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4595",
            "title": "cursor researching: Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Issue title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4595",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_invalid_payloads(self):
        for event in (None, [], "status_changed"):
            with self.subTest(event=event):
                self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
