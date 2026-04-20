import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4499",
      newStatus: "To Research",
      title: "Loss of H2",
    },
  });

  assert.deepEqual(result, {
    action: "update_issue_title",
    issueId: "POI-4499",
    title: "Cursor researching: Loss of H2",
  });
});

test("handleIssueStatusChanged returns null for non research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4499",
      newStatus: "In Progress",
      title: "Loss of H2",
    },
  });

  assert.equal(result, null);
});
