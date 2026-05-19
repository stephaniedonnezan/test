import unittest

from linear_research_title import (
    PayloadError,
    extract_issue_event,
    should_update_title,
    title_with_research_marker,
)


class ResearchTitleTests(unittest.TestCase):
    def test_should_update_only_for_to_research_without_existing_marker(self):
        self.assertTrue(should_update_title("To Research", "[]Site switch"))
        self.assertTrue(should_update_title("  to   research  ", "Site switch"))
        self.assertFalse(should_update_title("In Review", "[]Site switch"))
        self.assertFalse(
            should_update_title("To Research", "[Cursor researching] Site switch")
        )

    def test_replaces_empty_bracket_prefix(self):
        self.assertEqual(
            title_with_research_marker("[]Site switch on the site name"),
            "[Cursor researching] Site switch on the site name",
        )

    def test_prefixes_titles_without_empty_brackets(self):
        self.assertEqual(
            title_with_research_marker("Site switch on the site name"),
            "[Cursor researching] Site switch on the site name",
        )

    def test_extracts_cursor_automation_payload(self):
        event = extract_issue_event(
            {
                "triggerContext": {
                    "id": "POI-4660",
                    "title": "[]Site switch on the site name",
                    "newStatus": "To Research",
                }
            }
        )

        self.assertEqual(event.issue_id, "POI-4660")
        self.assertEqual(event.title, "[]Site switch on the site name")
        self.assertEqual(event.status, "To Research")

    def test_extracts_linear_webhook_payload(self):
        event = extract_issue_event(
            {
                "data": {
                    "id": "linear-uuid",
                    "identifier": "POI-4660",
                    "title": "Site switch on the site name",
                    "state": {"name": "To Research"},
                }
            }
        )

        self.assertEqual(event.issue_id, "linear-uuid")
        self.assertEqual(event.title, "Site switch on the site name")
        self.assertEqual(event.status, "To Research")

    def test_rejects_payload_without_issue_data(self):
        with self.assertRaises(PayloadError):
            extract_issue_event({"triggerContext": {"newStatus": "To Research"}})


if __name__ == "__main__":
    unittest.main()
