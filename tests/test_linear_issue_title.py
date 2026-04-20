import unittest

from automation.linear_issue_title import (
    build_linear_title_update,
    build_research_title,
    maybe_prefix_title_on_status_change,
)


class LinearIssueTitleTests(unittest.TestCase):
    def test_build_research_title_prefixes_when_missing(self) -> None:
        self.assertEqual(
            build_research_title("[Bug] Form submit fails"),
            "Cursor researching: [Bug] Form submit fails",
        )

    def test_build_research_title_is_idempotent(self) -> None:
        self.assertEqual(
            build_research_title("Cursor researching: [Bug] Form submit fails"),
            "Cursor researching: [Bug] Form submit fails",
        )

    def test_status_change_to_research_updates_title(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "[Bug] Form submit fails",
            }
        }
        self.assertEqual(
            maybe_prefix_title_on_status_change(payload),
            "Cursor researching: [Bug] Form submit fails",
        )

    def test_status_change_match_is_case_insensitive(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": " To   Research ",
                "title": "[Bug] Form submit fails",
            }
        }
        self.assertEqual(
            maybe_prefix_title_on_status_change(payload),
            "Cursor researching: [Bug] Form submit fails",
        )

    def test_non_matching_status_does_not_update_title(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "QA",
                "title": "[Bug] Form submit fails",
            }
        }
        self.assertIsNone(maybe_prefix_title_on_status_change(payload))

    def test_update_payload_contains_id_and_title(self) -> None:
        payload = {
            "triggerContext": {
                "id": "POI-4490",
                "newStatus": "to research",
                "title": "[Bug] Form submit fails",
            }
        }
        self.assertEqual(
            build_linear_title_update(payload),
            {
                "id": "POI-4490",
                "title": "Cursor researching: [Bug] Form submit fails",
            },
        )

    def test_update_payload_returns_none_without_issue_id(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "[Bug] Form submit fails",
            }
        }
        self.assertIsNone(build_linear_title_update(payload))


if __name__ == "__main__":
    unittest.main()
