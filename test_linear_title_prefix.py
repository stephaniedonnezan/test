import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4491",
                "title": "Cursor researching: N+1 Query",
            },
        )

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4491",
            "title": "N+1 Query",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: N+1 Query",
        )

    def test_falls_back_to_status_when_new_status_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: N+1 Query",
        )

    def test_accepts_issue_id_key(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4491")

    def test_normalizes_status_casing_and_separators(self):
        for status in ("To Research", "to_research", "to-research", "  TO   RESEARCH  "):
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": status,
                        "id": "POI-4491",
                        "title": "N+1 Query",
                    }
                }

                self.assertIsNotNone(build_issue_title_update(event))

    def test_normalizes_trigger_casing_and_separators(self):
        for trigger in ("Status Changed", "status-changed", "STATUS_CHANGED"):
            with self.subTest(trigger=trigger):
                event = {
                    "triggerContext": {
                        "trigger": trigger,
                        "newStatus": "to research",
                        "id": "POI-4491",
                        "title": "N+1 Query",
                    }
                }

                self.assertIsNotNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4491",
                "title": "Cursor researching: N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4491",
                "title": "cursor researching: N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "DEV",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4491",
                "title": "N+1 Query",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-4491 ",
                "title": "  N+1 Query  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4491",
                "title": "Cursor researching: N+1 Query",
            },
        )

    def test_ignores_payloads_missing_issue_id_or_title(self):
        missing_issue_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "N+1 Query",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4491",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_issue_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


if __name__ == "__main__":
    unittest.main()
