import json
import subprocess
import tempfile
import unittest

from linear_title_prefix import PREFIX, compute_updated_title


class ComputeUpdatedTitleTests(unittest.TestCase):
    def test_prefix_added_for_status_changed_to_research(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "delivery event and unloading event bug",
        }

        self.assertEqual(
            compute_updated_title(payload),
            f"{PREFIX}delivery event and unloading event bug",
        )

    def test_prefix_not_added_for_other_status(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "in progress",
            "title": "delivery event and unloading event bug",
        }

        self.assertEqual(
            compute_updated_title(payload), "delivery event and unloading event bug"
        )

    def test_prefix_not_added_for_other_trigger(self) -> None:
        payload = {
            "trigger": "issue_created",
            "newStatus": "to research",
            "title": "delivery event and unloading event bug",
        }

        self.assertEqual(
            compute_updated_title(payload), "delivery event and unloading event bug"
        )

    def test_existing_prefix_is_not_duplicated(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Cursor researching - delivery event and unloading event bug",
        }

        self.assertEqual(
            compute_updated_title(payload),
            "Cursor researching - delivery event and unloading event bug",
        )

    def test_existing_colon_prefix_is_not_duplicated(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "cursor researching: delivery event and unloading event bug",
        }

        self.assertEqual(
            compute_updated_title(payload),
            "cursor researching: delivery event and unloading event bug",
        )

    def test_nested_trigger_context_payload_shape(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "delivery event and unloading event bug",
            }
        }

        self.assertEqual(
            compute_updated_title(payload),
            f"{PREFIX}delivery event and unloading event bug",
        )

    def test_status_falls_back_to_status_field(self) -> None:
        payload = {
            "trigger": "status_changed",
            "status": "to research",
            "title": "delivery event and unloading event bug",
        }

        self.assertEqual(
            compute_updated_title(payload),
            f"{PREFIX}delivery event and unloading event bug",
        )

    def test_empty_title_uses_prefix_without_trailing_separator(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "",
        }

        self.assertEqual(compute_updated_title(payload), "Cursor researching")

    def test_non_string_values_are_normalized(self) -> None:
        payload = {
            "trigger": "STATUS-CHANGED",
            "newStatus": "To_Research",
            "title": "delivery event and unloading event bug",
        }

        self.assertEqual(
            compute_updated_title(payload),
            f"{PREFIX}delivery event and unloading event bug",
        )


class CliTests(unittest.TestCase):
    def test_cli_reads_input_file_and_prints_json(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "delivery event and unloading event bug",
        }

        with tempfile.NamedTemporaryFile("w+", suffix=".json") as handle:
            json.dump(payload, handle)
            handle.flush()
            result = subprocess.run(
                ["python3", "linear_title_prefix.py", "--input", handle.name],
                check=True,
                text=True,
                capture_output=True,
            )

        self.assertEqual(
            json.loads(result.stdout.strip()),
            {"updatedTitle": f"{PREFIX}delivery event and unloading event bug"},
        )


if __name__ == "__main__":
    unittest.main()
