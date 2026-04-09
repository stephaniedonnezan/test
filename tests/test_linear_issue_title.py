import unittest

from automation.linear_issue_title import (
    RESEARCH_PREFIX,
    build_prefixed_title,
    plan_title_update,
    should_prefix_title,
)


class ShouldPrefixTitleTests(unittest.TestCase):
    def test_requires_issue_status_change_trigger(self) -> None:
        payload = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "to research",
        }
        self.assertTrue(should_prefix_title(payload))

    def test_ignores_non_matching_trigger(self) -> None:
        payload = {
            "webhookType": "issue",
            "trigger": "comment_created",
            "newStatus": "to research",
        }
        self.assertFalse(should_prefix_title(payload))

    def test_normalizes_status_casing_and_spacing(self) -> None:
        payload = {
            "webhookType": "issue",
            "trigger": "status_changed",
            "newStatus": "  To   Research  ",
        }
        self.assertTrue(should_prefix_title(payload))


class BuildPrefixedTitleTests(unittest.TestCase):
    def test_adds_research_prefix(self) -> None:
        self.assertEqual(
            build_prefixed_title("Allow overrides in spreadsheets"),
            f"{RESEARCH_PREFIX} - Allow overrides in spreadsheets",
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        self.assertEqual(
            build_prefixed_title("cursor researching - Existing"),
            "cursor researching - Existing",
        )

    def test_blank_title_returns_prefix(self) -> None:
        self.assertEqual(build_prefixed_title("   "), RESEARCH_PREFIX)


class PlanTitleUpdateTests(unittest.TestCase):
    def test_supports_cursor_trigger_context_wrapper(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4382",
                "title": "Allow overrides",
            }
        }
        decision = plan_title_update(payload)
        self.assertTrue(decision.should_update)
        self.assertEqual(decision.identifier, "POI-4382")
        self.assertEqual(decision.new_title, "Cursor researching - Allow overrides")

    def test_no_update_when_status_is_not_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "in review",
                "id": "POI-4382",
                "title": "Allow overrides",
            }
        }
        decision = plan_title_update(payload)
        self.assertFalse(decision.should_update)
        self.assertEqual(decision.new_title, "Allow overrides")

    def test_no_update_when_identifier_missing(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Allow overrides",
            }
        }
        decision = plan_title_update(payload)
        self.assertFalse(decision.should_update)
        self.assertEqual(decision.new_title, "Allow overrides")


if __name__ == "__main__":
    unittest.main()
