import json
import unittest
from unittest import mock

from scripts.linear_research_title import (
    TITLE_MARKER,
    TitleUpdate,
    normalize_status,
    title_update_for_payload,
    update_linear_issue_title,
)


class LinearResearchTitleTests(unittest.TestCase):
    def test_normalize_status_handles_case_and_separators(self):
        self.assertEqual(normalize_status(" To-Research "), "to research")
        self.assertEqual(normalize_status("TO_RESEARCH"), "to research")

    def test_cursor_trigger_context_to_research_builds_title_update(self):
        payload = {
            "automationId": "automation-id",
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4753",
                "title": "Split CO2 export values",
            },
        }

        update = title_update_for_payload(payload)

        self.assertEqual(
            update,
            TitleUpdate(
                issue_id="POI-4753",
                old_title="Split CO2 export values",
                new_title=f"{TITLE_MARKER}: Split CO2 export values",
            ),
        )

    def test_linear_webhook_shape_to_research_builds_title_update(self):
        payload = {
            "type": "Issue",
            "action": "update",
            "data": {
                "id": "issue-id",
                "title": "Need research",
                "state": {"name": "to research"},
            },
        }

        update = title_update_for_payload(payload)

        self.assertIsNotNone(update)
        self.assertEqual(update.issue_id, "issue-id")
        self.assertEqual(update.new_title, f"{TITLE_MARKER}: Need research")

    def test_other_status_does_not_update(self):
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4753",
                "title": "Split CO2 export values",
            },
        }

        self.assertIsNone(title_update_for_payload(payload))

    def test_already_marked_title_does_not_update(self):
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4753",
                "title": f"{TITLE_MARKER}: Split CO2 export values",
            },
        }

        self.assertIsNone(title_update_for_payload(payload))

    @mock.patch("scripts.linear_research_title.urllib.request.urlopen")
    def test_update_linear_issue_title_posts_graphql_mutation(self, urlopen):
        response = mock.Mock()
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=None)
        response.read.return_value = json.dumps(
            {"data": {"issueUpdate": {"success": True, "issue": {"id": "issue-id"}}}}
        ).encode("utf-8")
        urlopen.return_value = response
        update = TitleUpdate(
            issue_id="issue-id",
            old_title="Title",
            new_title=f"{TITLE_MARKER}: Title",
        )

        result = update_linear_issue_title(update, "linear-api-key", api_url="https://linear.test/graphql")

        self.assertTrue(result["data"]["issueUpdate"]["success"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://linear.test/graphql")
        self.assertEqual(request.headers["Authorization"], "linear-api-key")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            body["variables"],
            {"issueId": "issue-id", "title": f"{TITLE_MARKER}: Title"},
        )


if __name__ == "__main__":
    unittest.main()
