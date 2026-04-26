import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    add_researching_prefix,
    needs_researching_prefix,
    normalized_value,
)


class NormalizedValueTest(unittest.TestCase):
    def test_normalizes_case_whitespace_and_separators(self):
        self.assertEqual(normalized_value(" To_Research "), "to research")
        self.assertEqual(normalized_value("to-research"), "to research")
        self.assertEqual(normalized_value("TO   RESEARCH"), "to research")

    def test_handles_none(self):
        self.assertEqual(normalized_value(None), "")


class NeedsResearchingPrefixTest(unittest.TestCase):
    def test_detects_missing_prefix(self):
        self.assertTrue(needs_researching_prefix("Add a table of Qualified Inputs"))

    def test_detects_existing_prefix_case_insensitively(self):
        self.assertFalse(needs_researching_prefix("Cursor researching: Add a table"))
        self.assertFalse(needs_researching_prefix("cursor researching - Add a table"))

    def test_empty_title_does_not_need_prefix(self):
        self.assertFalse(needs_researching_prefix(""))
        self.assertFalse(needs_researching_prefix(None))


class PrefixedTitleTest(unittest.TestCase):
    def test_adds_cursor_researching_prefix(self):
        self.assertEqual(
            add_researching_prefix("Add a table of Qualified Inputs"),
            f"{TITLE_PREFIX}: Add a table of Qualified Inputs",
        )

    def test_does_not_duplicate_existing_prefix(self):
        title = "Cursor researching: Add a table"
        self.assertEqual(add_researching_prefix(title), title)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3998",
                "title": "Add a table of Qualified Inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3998",
                "title": "Cursor researching: Add a table of Qualified Inputs",
            },
        )

    def test_accepts_flat_event_shape(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-3998",
            "title": "Add a table of Qualified Inputs",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3998",
                "title": "Cursor researching: Add a table of Qualified Inputs",
            },
        )

    def test_accepts_status_fallback(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to-research",
                "id": "POI-3998",
                "title": "Add a table of Qualified Inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3998",
                "title": "Cursor researching: Add a table of Qualified Inputs",
            },
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3998",
                "title": "Add a table of Qualified Inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_research_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-3998",
                "title": "Add a table of Qualified Inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3998",
                "title": "Cursor researching: Add a table of Qualified Inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Add a table of Qualified Inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
