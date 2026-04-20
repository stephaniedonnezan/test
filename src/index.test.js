import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4494",
      newStatus: "To Research",
      title: "Add a Delete button on the Container Events Table",
    },
  });

  assert.deepEqual(result, {
    action: "update_issue_title",
    issueId: "POI-4494",
    title: "Cursor researching: Add a Delete button on the Container Events Table",
  });
});

test("handleIssueStatusChanged returns null for non research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4494",
      newStatus: "In Progress",
      title: "Add a Delete button on the Container Events Table",
    },
  });

  assert.equal(result, null);
});
