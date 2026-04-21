import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    build_title_update,
    ensure_research_prefix,
    has_research_prefix,
)


class EnsureResearchPrefixTests(unittest.TestCase):
    def test_adds_prefix_when_missing(self) -> None:
        self.assertEqual(
            ensure_research_prefix("Implement Certifhy chip in audit"),
            f"{RESEARCH_PREFIX}: Implement Certifhy chip in audit",
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        prefixed = f"{RESEARCH_PREFIX}: Implement Certifhy chip in audit"
        self.assertEqual(ensure_research_prefix(prefixed), prefixed)


class HasResearchPrefixTests(unittest.TestCase):
    def test_matches_case_insensitive_prefix(self) -> None:
        self.assertTrue(has_research_prefix("cursor researching: title"))
        self.assertTrue(has_research_prefix("Cursor researching title"))

    def test_rejects_non_prefix_occurrences(self) -> None:
        self.assertFalse(has_research_prefix("Researching cursor title"))


class BuildTitleUpdateTests(unittest.TestCase):
    def test_returns_none_for_non_status_change(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "created",
                "newStatus": "to research",
                "title": "Implement Certifhy chip in audit",
                "id": "POI-4502",
            }
        }
        self.assertIsNone(build_title_update(payload))

    def test_returns_none_for_non_research_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "in progress",
                "title": "Implement Certifhy chip in audit",
                "id": "POI-4502",
            }
        }
        self.assertIsNone(build_title_update(payload))

    def test_returns_update_for_status_changed_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Implement Certifhy chip in audit",
                "id": "POI-4502",
            }
        }
        update = build_title_update(payload)
        self.assertIsNotNone(update)
        assert update is not None
        self.assertEqual(update.issue_id, "POI-4502")
        self.assertEqual(update.previous_title, "Implement Certifhy chip in audit")
        self.assertEqual(
            update.next_title,
            f"{RESEARCH_PREFIX}: Implement Certifhy chip in audit",
        )

    def test_returns_none_when_already_prefixed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": f"{RESEARCH_PREFIX}: Implement Certifhy chip in audit",
                "id": "POI-4502",
            }
        }
        self.assertIsNone(build_title_update(payload))


if __name__ == "__main__":
    unittest.main()
