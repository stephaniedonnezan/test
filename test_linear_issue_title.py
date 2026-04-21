import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    build_title_update,
    ensure_research_prefix,
)


class EnsureResearchPrefixTests(unittest.TestCase):
    def test_adds_prefix_when_missing(self) -> None:
        self.assertEqual(
            ensure_research_prefix("Ensure we can re-open a delivery"),
            f"{RESEARCH_PREFIX} - Ensure we can re-open a delivery",
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        prefixed = f"{RESEARCH_PREFIX} - Ensure we can re-open a delivery"
        self.assertEqual(ensure_research_prefix(prefixed), prefixed)


class BuildTitleUpdateTests(unittest.TestCase):
    def test_returns_none_for_non_research_status(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "In Review",
                "title": "Ensure we can re-open a delivery",
            }
        }
        self.assertIsNone(build_title_update(payload))

    def test_returns_update_when_status_becomes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "Ensure we can re-open a delivery",
            }
        }
        update = build_title_update(payload)
        self.assertIsNotNone(update)
        assert update is not None
        self.assertEqual(
            update.title,
            f"{RESEARCH_PREFIX} - Ensure we can re-open a delivery",
        )

    def test_returns_none_when_title_already_prefixed(self) -> None:
        prefixed_title = f"{RESEARCH_PREFIX} - Ensure we can re-open a delivery"
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": prefixed_title,
            }
        }
        self.assertIsNone(build_title_update(payload))


if __name__ == "__main__":
    unittest.main()
