import unittest

from linear_title_prefix import handle_issue_status_changed


class HandleIssueStatusChangedTests(unittest.TestCase):
    def test_returns_update_payload_when_matching(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4529",
                "title": "Investigate producer data mapping",
            }
        }
        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4529",
                "title": "Cursor researching: Investigate producer data mapping",
            },
        )

    def test_handles_case_and_separator_variants(self):
        event = {
            "triggerContext": {
                "trigger": "status-changed",
                "newStatus": "To_Research",
                "id": "POI-4529",
                "title": "Investigate producer data mapping",
            }
        }
        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4529",
                "title": "Cursor researching: Investigate producer data mapping",
            },
        )

    def test_uses_status_fallback_when_new_status_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-100",
                "title": "Top level issue title",
            }
        }
        self.assertEqual(
            handle_issue_status_changed(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-100",
                "title": "Cursor researching: Top level issue title",
            },
        )

    def test_noop_when_already_prefixed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4529",
                "title": "cursor researching: Existing title",
            }
        }
        self.assertIsNone(handle_issue_status_changed(event))

    def test_returns_none_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "todo",
                "id": "POI-4529",
                "title": "Investigate producer data mapping",
            }
        }
        self.assertIsNone(handle_issue_status_changed(event))

    def test_returns_none_for_other_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-4529",
                "title": "Investigate producer data mapping",
            }
        }
        self.assertIsNone(handle_issue_status_changed(event))

    def test_returns_none_when_missing_required_fields(self):
        self.assertIsNone(handle_issue_status_changed(None))
        self.assertIsNone(handle_issue_status_changed({}))
        self.assertIsNone(
            handle_issue_status_changed(
                {"triggerContext": {"trigger": "status_changed", "newStatus": "to research"}}
            )
        )


if __name__ == "__main__":
    unittest.main()
