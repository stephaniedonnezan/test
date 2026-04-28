import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3006",
                    "title": "Checklist for GHG&MB deepdive",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3006",
                "title": "Cursor researching: Checklist for GHG&MB deepdive",
            },
        )

    def test_accepts_flat_payloads(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3006",
                "title": "Checklist for GHG&MB deepdive",
            }
        )

        self.assertEqual(result["issueId"], "POI-3006")
        self.assertEqual(result["title"], "Cursor researching: Checklist for GHG&MB deepdive")

    def test_falls_back_to_status_when_new_status_is_missing(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "status": "to research",
                    "id": "POI-3006",
                    "title": "Checklist for GHG&MB deepdive",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Checklist for GHG&MB deepdive")

    def test_accepts_issue_id_when_id_is_missing(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "issueId": "POI-3006",
                    "title": "Checklist for GHG&MB deepdive",
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-3006")

    def test_matches_status_case_and_separator_variants(self):
        for status in ("To Research", "to_research", "to-research", "  TO   RESEARCH  "):
            with self.subTest(status=status):
                result = build_issue_title_update(
                    {
                        "triggerContext": {
                            "trigger": "status_changed",
                            "newStatus": status,
                            "id": "POI-3006",
                            "title": "Checklist for GHG&MB deepdive",
                        }
                    }
                )

                self.assertIsNotNone(result)

    def test_matches_trigger_case_and_separator_variants(self):
        for trigger in ("Status Changed", "status-changed", "STATUS_CHANGED"):
            with self.subTest(trigger=trigger):
                result = build_issue_title_update(
                    {
                        "triggerContext": {
                            "trigger": trigger,
                            "newStatus": "to research",
                            "id": "POI-3006",
                            "title": "Checklist for GHG&MB deepdive",
                        }
                    }
                )

                self.assertIsNotNone(result)

    def test_skips_non_status_change_triggers(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-3006",
                    "title": "Checklist for GHG&MB deepdive",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Canceled",
                    "id": "POI-3006",
                    "title": "Checklist for GHG&MB deepdive",
                }
            }
        )

        self.assertIsNone(result)

    def test_skips_already_prefixed_titles_case_insensitively(self):
        for title in (
            "Cursor researching: Checklist for GHG&MB deepdive",
            "cursor researching Checklist for GHG&MB deepdive",
        ):
            with self.subTest(title=title):
                result = build_issue_title_update(
                    {
                        "triggerContext": {
                            "trigger": "status_changed",
                            "newStatus": "to research",
                            "id": "POI-3006",
                            "title": title,
                        }
                    }
                )

                self.assertIsNone(result)

    def test_skips_events_without_issue_id_or_title(self):
        for trigger_context in (
            {"trigger": "status_changed", "newStatus": "to research", "title": "A title"},
            {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3006"},
            {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3006", "title": "   "},
        ):
            with self.subTest(trigger_context=trigger_context):
                self.assertIsNone(build_issue_title_update({"triggerContext": trigger_context}))

    def test_ignores_non_mapping_payloads(self):
        for event in (None, [], "event"):
            with self.subTest(event=event):
                self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
