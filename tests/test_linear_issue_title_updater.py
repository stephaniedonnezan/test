import unittest

from scripts.linear_issue_title_updater import (
    build_prefixed_title,
    build_title_update,
    should_update_title,
    title_has_prefix,
)


class LinearIssueTitleUpdaterTests(unittest.TestCase):
    def test_title_has_prefix_case_insensitive(self) -> None:
        self.assertTrue(title_has_prefix("cursor researching: Example issue"))
        self.assertTrue(title_has_prefix("  Cursor Researching: Example issue"))
        self.assertFalse(title_has_prefix("Example issue"))

    def test_build_prefixed_title_only_once(self) -> None:
        self.assertEqual(
            build_prefixed_title("Meter gap detection"),
            "Cursor researching: Meter gap detection",
        )
        self.assertEqual(
            build_prefixed_title("Cursor researching: Meter gap detection"),
            "Cursor researching: Meter gap detection",
        )

    def test_should_update_title_requires_target_status(self) -> None:
        self.assertFalse(should_update_title("Todo", "Issue title"))
        self.assertTrue(should_update_title("to research", "Issue title"))
        self.assertTrue(should_update_title("To Research", "Issue title"))
        self.assertFalse(
            should_update_title("to research", "Cursor researching: Issue title")
        )
        self.assertFalse(should_update_title("to research", ""))

    def test_build_title_update_from_payload(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "[Phase 1] Gap detection in meter readings",
                "id": "POI-4445",
            }
        }
        self.assertEqual(
            build_title_update(payload),
            {
                "identifier": "POI-4445",
                "old_title": "[Phase 1] Gap detection in meter readings",
                "new_title": "Cursor researching: [Phase 1] Gap detection in meter readings",
            },
        )

    def test_build_title_update_returns_none_if_not_needed(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "Todo",
                "title": "[Phase 1] Gap detection in meter readings",
                "id": "POI-4445",
            }
        }
        self.assertIsNone(build_title_update(payload))


if __name__ == "__main__":
    unittest.main()
