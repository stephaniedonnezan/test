import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    add_research_prefix,
    build_title_update,
    build_title_update_from_payload,
    status_is_to_research,
)


class LinearIssueTitleTests(unittest.TestCase):
    def test_status_match_is_case_and_whitespace_insensitive(self) -> None:
        self.assertTrue(status_is_to_research("to research"))
        self.assertTrue(status_is_to_research("  To   Research "))
        self.assertFalse(status_is_to_research("qa"))

    def test_add_prefix_only_once(self) -> None:
        title = "delivery event and unloading event bug"
        prefixed = add_research_prefix(title)
        self.assertEqual(
            prefixed,
            f"{RESEARCH_PREFIX}: delivery event and unloading event bug",
        )
        self.assertEqual(add_research_prefix(prefixed), prefixed)

    def test_build_title_update_returns_none_for_other_statuses(self) -> None:
        title = "delivery event and unloading event bug"
        self.assertIsNone(build_title_update(title=title, new_status="QA"))

    def test_build_title_update_returns_none_when_already_prefixed(self) -> None:
        title = f"{RESEARCH_PREFIX}: delivery event and unloading event bug"
        self.assertIsNone(build_title_update(title=title, new_status="to research"))

    def test_payload_mapping_from_trigger_context(self) -> None:
        payload = {
            "triggerContext": {
                "id": "POI-4464",
                "title": "delivery event and unloading event bug",
                "newStatus": "to research",
            }
        }
        result = build_title_update_from_payload(payload)
        self.assertEqual(result["issue_id"], "POI-4464")
        self.assertTrue(result["should_update"])
        self.assertEqual(
            result["new_title"],
            f"{RESEARCH_PREFIX}: delivery event and unloading event bug",
        )

    def test_payload_mapping_uses_root_keys_as_fallback(self) -> None:
        payload = {
            "id": "POI-4464",
            "title": "delivery event and unloading event bug",
            "newStatus": "qa",
        }
        result = build_title_update_from_payload(payload)
        self.assertFalse(result["should_update"])
        self.assertEqual(result["new_title"], "delivery event and unloading event bug")


if __name__ == "__main__":
    unittest.main()
