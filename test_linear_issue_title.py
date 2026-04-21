import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    apply_status_title_rule,
    updated_title_from_trigger_payload,
)


class ApplyStatusTitleRuleTests(unittest.TestCase):
    def test_adds_prefix_when_status_is_to_research(self) -> None:
        title = "Investigate transport segment mismatch"
        result = apply_status_title_rule(title=title, new_status="to research")
        self.assertEqual(result, f"{RESEARCH_PREFIX} - {title}")

    def test_keeps_title_when_status_is_not_to_research(self) -> None:
        title = "Investigate transport segment mismatch"
        result = apply_status_title_rule(title=title, new_status="DEV")
        self.assertEqual(result, title)

    def test_does_not_duplicate_prefix(self) -> None:
        title = f"{RESEARCH_PREFIX} - Investigate transport segment mismatch"
        result = apply_status_title_rule(title=title, new_status="to research")
        self.assertEqual(result, title)

    def test_normalizes_status_whitespace_and_case(self) -> None:
        title = "Investigate transport segment mismatch"
        result = apply_status_title_rule(title=title, new_status="  To Research ")
        self.assertEqual(result, f"{RESEARCH_PREFIX} - {title}")


class UpdatedTitleFromPayloadTests(unittest.TestCase):
    def test_uses_trigger_context_fields(self) -> None:
        payload = {
            "triggerContext": {
                "title": "Issue title",
                "newStatus": "to research",
            }
        }
        self.assertEqual(
            updated_title_from_trigger_payload(payload),
            f"{RESEARCH_PREFIX} - Issue title",
        )

    def test_handles_missing_trigger_context_keys(self) -> None:
        self.assertEqual(updated_title_from_trigger_payload({}), "")


if __name__ == "__main__":
    unittest.main()
