import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_issue_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4561",
                "title": "Inputs disappear in mass balance view when output is locked",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4561",
                "title": (
                    "Cursor researching: Inputs disappear in mass balance view "
                    "when output is locked"
                ),
            },
        )

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "Investigate widgets",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate widgets",
            },
        )

    def test_accepts_issue_id_when_id_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-2",
                "title": "Investigate calculations",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-2",
        )

    def test_uses_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-3",
                "title": "Investigate event payloads",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate event payloads",
        )

    def test_normalizes_trigger_and_status_separators(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "To-Research",
                "id": "POI-4",
                "title": "Investigate casing",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate casing",
        )

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5",
                "title": "  Investigate whitespace  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate whitespace",
        )

    def test_skips_when_status_does_not_match(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-6",
                "title": "Investigate later",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_when_trigger_does_not_match(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-7",
                "title": "Investigate creation",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-8",
                "title": "cursor researching: Investigate duplicates",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_identifier(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate missing id",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_non_empty_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-9",
                "title": "   ",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
