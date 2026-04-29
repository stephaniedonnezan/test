import unittest

from linear_title_prefix import CURSOR_RESEARCHING_PREFIX, build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4553",
                "title": "Add API to update document extractions results",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4553",
                "title": "Cursor researching: Add API to update document extractions results",
            },
        )

    def test_supports_flat_payload_shape(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "to_research",
            "issueId": "POI-1",
            "title": "Investigate connection issue",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-1")
        self.assertEqual(result["title"], "Cursor researching: Investigate connection issue")

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS CHANGED",
                "status": "to research",
                "id": "POI-2",
                "title": "Research me",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research me",
        )

    def test_returns_none_for_non_status_changed_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-3",
                "title": "Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_status_other_than_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4",
                "title": "Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_already_prefixed(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "cursor researching: Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-6",
                "title": "  Research me  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{CURSOR_RESEARCHING_PREFIX}: Research me",
        )

    def test_returns_none_without_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Research me",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-7",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not an event"))


if __name__ == "__main__":
    unittest.main()
