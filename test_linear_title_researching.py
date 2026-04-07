import unittest

from linear_title_researching import build_updated_title, should_mark_issue


class ShouldMarkIssueTests(unittest.TestCase):
    def test_marks_when_status_is_exact_to_research(self) -> None:
        payload = {"triggerContext": {"newStatus": "to research"}}
        self.assertTrue(should_mark_issue(payload))

    def test_marks_when_status_is_case_and_space_variant(self) -> None:
        payload = {"triggerContext": {"newStatus": "  To   Research "}}
        self.assertTrue(should_mark_issue(payload))

    def test_does_not_mark_for_other_status(self) -> None:
        payload = {"triggerContext": {"newStatus": "In Review"}}
        self.assertFalse(should_mark_issue(payload))


class BuildUpdatedTitleTests(unittest.TestCase):
    def test_prefixes_marker_when_missing(self) -> None:
        self.assertEqual(
            build_updated_title("Spreadsheet testing"), "Cursor researching Spreadsheet testing"
        )

    def test_does_not_duplicate_existing_marker(self) -> None:
        self.assertEqual(
            build_updated_title("Cursor researching Spreadsheet testing"),
            "Cursor researching Spreadsheet testing",
        )

    def test_existing_marker_is_detected_case_insensitively(self) -> None:
        self.assertEqual(
            build_updated_title("cursor researching Spreadsheet testing"),
            "cursor researching Spreadsheet testing",
        )


if __name__ == "__main__":
    unittest.main()
