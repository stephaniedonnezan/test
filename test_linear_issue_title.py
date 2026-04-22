import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    build_linear_title_update,
    updated_issue_title,
)


class LinearIssueTitleTests(unittest.TestCase):
    def test_adds_prefix_when_new_status_is_to_research(self) -> None:
        trigger_context = {
            "id": "POI-4329",
            "title": "Single POS issuance",
            "newStatus": "to research",
        }

        self.assertEqual(
            updated_issue_title(trigger_context),
            f"{RESEARCH_PREFIX}: Single POS issuance",
        )

    def test_status_normalization_accepts_different_formatting(self) -> None:
        trigger_context = {
            "id": "POI-4329",
            "title": "Single POS issuance",
            "newStatus": "To_Research",
        }

        payload = build_linear_title_update(trigger_context)
        self.assertEqual(
            payload,
            {"id": "POI-4329", "title": f"{RESEARCH_PREFIX}: Single POS issuance"},
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        trigger_context = {
            "id": "POI-4329",
            "title": "Cursor researching: Single POS issuance",
            "newStatus": "to research",
        }

        self.assertIsNone(build_linear_title_update(trigger_context))

    def test_uses_status_when_new_status_missing(self) -> None:
        trigger_context = {
            "id": "POI-4329",
            "title": "Single POS issuance",
            "status": "to research",
        }

        payload = build_linear_title_update(trigger_context)
        self.assertEqual(
            payload,
            {"id": "POI-4329", "title": f"{RESEARCH_PREFIX}: Single POS issuance"},
        )

    def test_non_research_status_keeps_title_unchanged(self) -> None:
        trigger_context = {
            "id": "POI-4329",
            "title": "Single POS issuance",
            "newStatus": "Canceled",
        }

        self.assertIsNone(build_linear_title_update(trigger_context))


if __name__ == "__main__":
    unittest.main()
