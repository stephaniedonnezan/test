import unittest

from linear_issue_title import (
    RESEARCH_TITLE_PREFIX,
    add_research_prefix,
    build_linear_title_update_payload,
    update_issue_title_for_status_change,
)


class UpdateIssueTitleForStatusChangeTests(unittest.TestCase):
    def test_adds_prefix_when_status_is_to_research(self) -> None:
        title = "Improve H2_NOT_GREEN_ENOUGH warning"
        updated = update_issue_title_for_status_change(title, "To Research")
        self.assertEqual(updated, f"{RESEARCH_TITLE_PREFIX} {title}")

    def test_does_not_change_title_for_other_status(self) -> None:
        title = "Improve H2_NOT_GREEN_ENOUGH warning"
        updated = update_issue_title_for_status_change(title, "In Progress")
        self.assertEqual(updated, title)

    def test_does_not_duplicate_prefix(self) -> None:
        title = "Cursor researching Improve H2_NOT_GREEN_ENOUGH warning"
        updated = update_issue_title_for_status_change(title, "To Research")
        self.assertEqual(updated, title)

    def test_status_match_is_case_and_whitespace_insensitive(self) -> None:
        title = "Improve H2_NOT_GREEN_ENOUGH warning"
        updated = update_issue_title_for_status_change(title, "  to   research ")
        self.assertEqual(updated, f"{RESEARCH_TITLE_PREFIX} {title}")


class BuildLinearTitleUpdatePayloadTests(unittest.TestCase):
    def test_builds_payload_when_title_changes(self) -> None:
        event = {
            "triggerContext": {
                "id": "POI-3330",
                "title": "Improve H2_NOT_GREEN_ENOUGH warning",
                "newStatus": "To Research",
            }
        }
        payload = build_linear_title_update_payload(event)
        self.assertEqual(
            payload,
            {
                "id": "POI-3330",
                "title": "Cursor researching Improve H2_NOT_GREEN_ENOUGH warning",
            },
        )

    def test_returns_none_when_title_unchanged(self) -> None:
        event = {
            "triggerContext": {
                "id": "POI-3330",
                "title": "Cursor researching Improve H2_NOT_GREEN_ENOUGH warning",
                "newStatus": "To Research",
            }
        }
        payload = build_linear_title_update_payload(event)
        self.assertIsNone(payload)

    def test_returns_none_when_required_fields_missing(self) -> None:
        event = {"triggerContext": {"newStatus": "To Research"}}
        payload = build_linear_title_update_payload(event)
        self.assertIsNone(payload)


class AddResearchPrefixTests(unittest.TestCase):
    def test_returns_prefix_for_blank_title(self) -> None:
        self.assertEqual(add_research_prefix("   "), RESEARCH_TITLE_PREFIX)


if __name__ == "__main__":
    unittest.main()
