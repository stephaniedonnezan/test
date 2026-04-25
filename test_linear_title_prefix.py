import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    has_research_prefix,
    prefix_research_title,
)


class PrefixResearchTitleTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix(self):
        self.assertEqual(
            prefix_research_title("[FE] Trader - Add delivery flow"),
            "Cursor researching: [FE] Trader - Add delivery flow",
        )

    def test_does_not_duplicate_existing_prefix(self):
        self.assertEqual(
            prefix_research_title("Cursor researching: [FE] Trader - Add delivery flow"),
            "Cursor researching: [FE] Trader - Add delivery flow",
        )

    def test_existing_prefix_check_is_case_insensitive(self):
        self.assertEqual(
            prefix_research_title("cursor researching - [FE] Trader - Add delivery flow"),
            "cursor researching - [FE] Trader - Add delivery flow",
        )

    def test_strips_outer_title_whitespace_before_prefixing(self):
        self.assertEqual(
            prefix_research_title("  [FE] Trader - Add delivery flow  "),
            "Cursor researching: [FE] Trader - Add delivery flow",
        )

    def test_empty_title_uses_prefix_only(self):
        self.assertEqual(prefix_research_title(" "), f"{TITLE_PREFIX}:")

    def test_detects_existing_prefix(self):
        self.assertTrue(has_research_prefix("  cursor researching: title"))
        self.assertFalse(has_research_prefix("Cursor researched: title"))


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_update_payload_for_matching_event(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-2838",
                "title": "[FE] Trader - Add delivery flow",
                "url": "https://linear.app/atmen/issue/POI-2838/fe-trader-add-delivery-flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2838",
                "title": "Cursor researching: [FE] Trader - Add delivery flow",
            },
        )

    def test_accepts_status_fallback(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-2838",
                "title": "[FE] Trader - Add delivery flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2838",
                "title": "Cursor researching: [FE] Trader - Add delivery flow",
            },
        )

    def test_normalizes_trigger_separators_and_status_case(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS-CHANGED",
                "newStatus": "  To   Research  ",
                "id": "POI-2838",
                "title": "[FE] Trader - Add delivery flow",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2838",
                "title": "Cursor researching: [FE] Trader - Add delivery flow",
            },
        )

    def test_returns_none_for_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-2838",
                "title": "[FE] Trader - Add delivery flow",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_other_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-2838",
                "title": "[FE] Trader - Add delivery flow",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_already_prefixed_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2838",
                "title": "Cursor researching: [FE] Trader - Add delivery flow",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_trigger_context(self):
        self.assertIsNone(build_issue_title_update({"trigger": "status_changed"}))


if __name__ == "__main__":
    unittest.main()
