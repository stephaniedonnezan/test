import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Restore DB snapshot from production in local",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4560",
                "title": "Cursor researching: Restore DB snapshot from production in local",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4560",
            "title": "Investigate production data",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate production data",
        )

    def test_accepts_issue_id_fallback(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4560",
                "title": "Investigate production data",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4560")

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4560",
                "title": "Investigate production data",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate production data",
        )

    def test_matches_status_case_and_separator_variants(self):
        for status in ("To Research", "to_research", "TO-RESEARCH", "  to   research  "):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": status,
                        "id": "POI-4560",
                        "title": "Investigate production data",
                    }
                }

                self.assertIsNotNone(build_issue_title_update(event))

    def test_matches_trigger_case_and_separator_variants(self):
        for trigger in ("status_changed", "Status Changed", "STATUS-CHANGED"):
            with self.subTest(trigger=trigger):
                event = {
                    "triggerContext": {
                        "trigger": trigger,
                        "newStatus": "to research",
                        "id": "POI-4560",
                        "title": "Investigate production data",
                    }
                }

                self.assertIsNotNone(build_issue_title_update(event))

    def test_skips_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4560",
                "title": "Investigate production data",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_updated",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "Investigate production data",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_avoids_duplicate_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "cursor researching: Investigate production data",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4560",
                "title": "  Investigate production data  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate production data",
        )

    def test_skips_missing_required_issue_fields(self):
        base_context = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4560",
            "title": "Investigate production data",
        }
        for field in ("id", "title"):
            with self.subTest(field=field):
                context = dict(base_context)
                context.pop(field)

                self.assertIsNone(build_issue_title_update({"triggerContext": context}))

    def test_ignores_non_mapping_events(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("status_changed"))


if __name__ == "__main__":
    unittest.main()
