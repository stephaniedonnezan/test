import unittest

from linear_issue_title_updater import (
    RESEARCH_PREFIX,
    update_issue_title_on_status_change,
)


class UpdateIssueTitleOnStatusChangeTests(unittest.TestCase):
    def test_returns_title_update_when_status_moves_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Indicative view on GHG emissions",
                "id": "POI-3804",
            }
        }

        result = update_issue_title_on_status_change(payload)

        self.assertEqual(
            result,
            {
                "issueId": "POI-3804",
                "oldTitle": "Indicative view on GHG emissions",
                "newTitle": f"{RESEARCH_PREFIX} - Indicative view on GHG emissions",
            },
        )

    def test_is_case_and_whitespace_insensitive_for_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "  To   Research  ",
                "title": "My issue",
                "id": "POI-1",
            }
        }

        result = update_issue_title_on_status_change(payload)

        self.assertEqual(result["newTitle"], f"{RESEARCH_PREFIX} - My issue")

    def test_does_not_duplicate_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": f"{RESEARCH_PREFIX} - Existing title",
                "id": "POI-1",
            }
        }

        result = update_issue_title_on_status_change(payload)

        self.assertIsNone(result)

    def test_returns_none_for_non_matching_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "title": "Title",
                "id": "POI-1",
            }
        }

        result = update_issue_title_on_status_change(payload)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
