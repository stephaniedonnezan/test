import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_title_update_for_nested_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4198",
                "title": "Cursor researching: Allow UBA POS creation for methane",
            },
        )

    def test_accepts_flat_payload_shape(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4198",
            "title": "Allow UBA POS creation for methane",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4198",
                "title": "Cursor researching: Allow UBA POS creation for methane",
            },
        )

    def test_accepts_issue_id_when_id_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-4198",
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allow UBA POS creation for methane",
        )

    def test_normalizes_status_trigger_and_whitespace(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "newStatus": "  To   Research  ",
                "id": "POI-4198",
                "title": "  Allow UBA POS creation for methane  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Allow UBA POS creation for methane",
        )

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4198",
                "title": "cursor researching: Allow UBA POS creation for methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Allow UBA POS creation for methane",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_blank_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4198",
                "title": "   ",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
