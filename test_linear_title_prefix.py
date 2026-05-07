import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_nested_trigger_context_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4558",
                "title": "Can we skip the intermediate POS when Trader is same legal entity as producer?",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4558",
                "title": "Cursor researching: Can we skip the intermediate POS when Trader is same legal entity as producer?",
            },
        )

    def test_prefixes_title_for_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-1",
            "title": "Investigate charge calculation",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-1",
                "title": "Cursor researching: Investigate charge calculation",
            },
        )

    def test_accepts_camel_case_status_changed_action(self):
        event = {
            "action": "statusChanged",
            "newStatus": "to research",
            "id": "POI-2",
            "title": "Investigate trip export",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2",
                "title": "Cursor researching: Investigate trip export",
            },
        )

    def test_accepts_research_status_with_separators_and_case_variants(self):
        for status in ("To Research", "to_research", "to-research", "toResearch"):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "newStatus": status,
                    "id": "POI-3",
                    "title": "Review Linear automation",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Review Linear automation",
                )

    def test_uses_status_fallback_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "to research",
            "id": "POI-4",
            "title": "Fallback status payload",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Fallback status payload",
        )

    def test_uses_state_name_fallback_when_status_fields_are_absent(self):
        event = {
            "trigger": "status_changed",
            "state": {"name": "to research"},
            "id": "POI-5",
            "title": "State name payload",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: State name payload",
        )

    def test_reads_nested_linear_data_issue_payload(self):
        event = {
            "data": {
                "action": "statusChanged",
                "newStatus": "to research",
                "issue": {
                    "id": "POI-6",
                    "title": "Nested issue payload",
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-6",
                "title": "Cursor researching: Nested issue payload",
            },
        )

    def test_outer_payload_fields_override_nested_issue_fields(self):
        event = {
            "data": {
                "action": "statusChanged",
                "newStatus": "done",
                "issue": {
                    "id": "POI-7",
                    "title": "Nested title",
                },
            },
            "newStatus": "to research",
            "title": "Outer title",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Outer title",
        )

    def test_accepts_issue_id_fallbacks(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": "POI-8",
            "title": "Issue ID fallback",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-8")

    def test_accepts_identifier_fallback(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "identifier": "POI-9",
            "title": "Identifier fallback",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-9")

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-10 ",
            "title": "  Trimmed title  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-10",
                "title": "Cursor researching: Trimmed title",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "QA",
            "id": "POI-11",
            "title": "Not a research issue",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-12",
            "title": "Comment event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-13",
            "title": "cursor researching: Existing title",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payloads_without_required_title_or_id(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-14",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Missing id",
                }
            )
        )
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
