import unittest

from linear_title_prefix import build_issue_title_update


def make_event(**overrides):
    trigger_context = {
        "trigger": "status_changed",
        "newStatus": "to research",
        "title": "Improve onboarding flow",
        "id": "POI-123",
    }
    trigger_context.update(overrides.pop("trigger_context", {}))

    event = {"triggerContext": trigger_context}
    event.update(overrides)
    return event


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_issue_moves_to_research(self):
        result = build_issue_title_update(make_event())

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Improve onboarding flow",
            },
        )

    def test_uses_flat_event_payloads(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Audit checkout",
                "id": "POI-456",
            }
        )

        self.assertEqual(result["issueId"], "POI-456")
        self.assertEqual(result["title"], "Cursor researching: Audit checkout")

    def test_returns_none_for_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_uses_status_when_new_status_is_absent(self):
        result = build_issue_title_update(
            make_event(trigger_context={"newStatus": None, "status": "to research"})
        )

        self.assertEqual(result["title"], "Cursor researching: Improve onboarding flow")

    def test_accepts_status_case_and_separator_variants(self):
        result = build_issue_title_update(
            make_event(trigger_context={"newStatus": " To-Research "})
        )

        self.assertEqual(result["title"], "Cursor researching: Improve onboarding flow")

    def test_accepts_trigger_case_and_separator_variants(self):
        result = build_issue_title_update(
            make_event(trigger_context={"trigger": "STATUS CHANGED"})
        )

        self.assertEqual(result["title"], "Cursor researching: Improve onboarding flow")

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            make_event(trigger_context={"title": "Cursor researching: Improve onboarding flow"})
        )

        self.assertIsNone(result)

    def test_existing_prefix_check_is_case_insensitive(self):
        result = build_issue_title_update(
            make_event(trigger_context={"title": "cursor researching - Improve onboarding flow"})
        )

        self.assertIsNone(result)

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(make_event(trigger_context={"newStatus": "DEV"}))

        self.assertIsNone(result)

    def test_ignores_other_triggers(self):
        result = build_issue_title_update(
            make_event(trigger_context={"trigger": "comment_created"})
        )

        self.assertIsNone(result)

    def test_requires_issue_identifier(self):
        result = build_issue_title_update(make_event(trigger_context={"id": None}))

        self.assertIsNone(result)

    def test_requires_title(self):
        result = build_issue_title_update(make_event(trigger_context={"title": ""}))

        self.assertIsNone(result)

    def test_supports_issue_id_field_name(self):
        result = build_issue_title_update(
            make_event(trigger_context={"id": None, "issueId": "POI-789"})
        )

        self.assertEqual(result["issueId"], "POI-789")


if __name__ == "__main__":
    unittest.main()
