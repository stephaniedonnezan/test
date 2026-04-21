import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    build_title_update,
    ensure_research_prefix,
)


class EnsureResearchPrefixTests(unittest.TestCase):
    def test_adds_prefix_when_missing(self) -> None:
        self.assertEqual(
            ensure_research_prefix("Investigate mass balance carryover"),
            f"{RESEARCH_PREFIX}: Investigate mass balance carryover",
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        prefixed = f"{RESEARCH_PREFIX}: Investigate mass balance carryover"
        self.assertEqual(ensure_research_prefix(prefixed), prefixed)

    def test_empty_title_becomes_prefix_only(self) -> None:
        self.assertEqual(ensure_research_prefix("   "), RESEARCH_PREFIX)


class BuildTitleUpdateTests(unittest.TestCase):
    def test_returns_none_for_non_research_status(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "in progress",
                "title": "Investigate mass balance carryover",
            }
        }
        self.assertIsNone(build_title_update(payload))

    def test_returns_update_when_status_becomes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "Investigate mass balance carryover",
            }
        }
        update = build_title_update(payload)
        self.assertIsNotNone(update)
        assert update is not None
        self.assertEqual(
            update.title,
            f"{RESEARCH_PREFIX}: Investigate mass balance carryover",
        )

    def test_status_match_is_case_insensitive(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "To Research",
                "title": "Investigate mass balance carryover",
            }
        }
        update = build_title_update(payload)
        self.assertIsNotNone(update)
        assert update is not None
        self.assertEqual(
            update.title,
            f"{RESEARCH_PREFIX}: Investigate mass balance carryover",
        )

    def test_returns_none_when_title_already_prefixed(self) -> None:
        prefixed_title = f"{RESEARCH_PREFIX}: Investigate mass balance carryover"
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": prefixed_title,
            }
        }
        self.assertIsNone(build_title_update(payload))


if __name__ == "__main__":
    unittest.main()
