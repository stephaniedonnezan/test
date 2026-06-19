import unittest

from linear_issue_title import RESEARCH_TITLE_MARKER
from linear_issue_title import add_research_marker_to_title
from linear_issue_title import title_for_status_change


class AddResearchMarkerToTitleTests(unittest.TestCase):
    def test_adds_marker_to_title(self) -> None:
        self.assertEqual(
            add_research_marker_to_title("Mass Balance items can't be filtered"),
            "Cursor researching: Mass Balance items can't be filtered",
        )

    def test_does_not_duplicate_existing_colon_marker(self) -> None:
        self.assertEqual(
            add_research_marker_to_title("Cursor researching: Existing title"),
            "Cursor researching: Existing title",
        )

    def test_does_not_duplicate_existing_hyphen_marker(self) -> None:
        self.assertEqual(
            add_research_marker_to_title("cursor researching - Existing title"),
            "cursor researching - Existing title",
        )

    def test_empty_title_becomes_marker(self) -> None:
        self.assertEqual(add_research_marker_to_title("   "), RESEARCH_TITLE_MARKER)


class TitleForStatusChangeTests(unittest.TestCase):
    def test_adds_marker_when_issue_changes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Mass Balance items can't be filtered",
            }
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching: Mass Balance items can't be filtered",
        )

    def test_accepts_root_level_trigger_context(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root payload title",
        }

        self.assertEqual(
            title_for_status_change(payload),
            "Cursor researching: Root payload title",
        )

    def test_status_match_accepts_whitespace_hyphen_and_underscore_variants(self) -> None:
        for new_status in ("  TO   RESEARCH  ", "to-research", "to_research"):
            with self.subTest(new_status=new_status):
                self.assertEqual(
                    title_for_status_change(
                        {
                            "triggerContext": {
                                "trigger": "status_changed",
                                "newStatus": new_status,
                                "title": "Variant title",
                            }
                        }
                    ),
                    "Cursor researching: Variant title",
                )

    def test_returns_none_for_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "No change",
            }
        }

        self.assertIsNone(title_for_status_change(payload))

    def test_returns_none_for_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "title": "No change",
            }
        }

        self.assertIsNone(title_for_status_change(payload))

    def test_returns_none_when_marker_already_exists(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Cursor researching: Existing title",
            }
        }

        self.assertIsNone(title_for_status_change(payload))

    def test_returns_none_for_missing_title_or_status(self) -> None:
        self.assertIsNone(title_for_status_change({"triggerContext": {"newStatus": "To Research"}}))
        self.assertIsNone(title_for_status_change({"triggerContext": {"title": "Missing status"}}))


if __name__ == "__main__":
    unittest.main()
