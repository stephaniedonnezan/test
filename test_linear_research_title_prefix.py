import unittest

from linear_research_title_prefix import (
    build_prefixed_title,
    extract_identifier,
    process_trigger_payload,
)


class TestLinearResearchTitlePrefix(unittest.TestCase):
    def test_build_prefixed_title_adds_prefix(self) -> None:
        new_title, changed = build_prefixed_title("Redispatch /Imbalance settlement")
        self.assertTrue(changed)
        self.assertEqual(new_title, "Cursor researching: Redispatch /Imbalance settlement")

    def test_build_prefixed_title_is_idempotent(self) -> None:
        title = "Cursor researching: Redispatch /Imbalance settlement"
        new_title, changed = build_prefixed_title(title)
        self.assertFalse(changed)
        self.assertEqual(new_title, title)

    def test_extract_identifier_from_url(self) -> None:
        trigger_context = {
            "url": "https://linear.app/atmen/issue/POI-4464/redispatch-imbalance-settlement",
        }
        self.assertEqual(extract_identifier(trigger_context), "POI-4464")

    def test_process_trigger_updates_when_to_research(self) -> None:
        calls: list[tuple[str, dict, str]] = []

        def fake_graphql(query: str, variables: dict, _api_key: str) -> dict:
            calls.append((query, variables, _api_key))
            if "query IssueById" in query:
                return {"issue": None}
            if "issueSearch" in query:
                return {
                    "issueSearch": {
                        "nodes": [
                            {
                                "id": "uuid-1",
                                "identifier": "POI-4464",
                                "title": "Delivery event and unloading event bug",
                            }
                        ]
                    }
                }
            if "issueUpdate" in query:
                return {
                    "issueUpdate": {
                        "success": True,
                        "issue": {
                            "id": "uuid-1",
                            "identifier": "POI-4464",
                            "title": variables["title"],
                        },
                    }
                }
            raise AssertionError("Unexpected query")

        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4464",
                "url": "https://linear.app/atmen/issue/POI-4464/delivery-event-and-unloading-event-bug",
            }
        }
        result = process_trigger_payload(payload, api_key="token", graphql_request=fake_graphql)
        self.assertTrue(result["updated"])
        self.assertEqual(result["title"], "Cursor researching: Delivery event and unloading event bug")
        self.assertEqual(len(calls), 3)

    def test_process_trigger_skips_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4464",
            }
        }
        result = process_trigger_payload(payload, api_key="token", graphql_request=lambda *_: {})
        self.assertFalse(result["updated"])
        self.assertEqual(result["reason"], "status was not to research")


if __name__ == "__main__":
    unittest.main()
