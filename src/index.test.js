import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4478",
      newStatus: "to research",
      title: "FIFO: Why are deliveries getting assigned so many sub batches?",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4478",
    title:
      "Cursor researching: FIFO: Why are deliveries getting assigned so many sub batches?",
  });
});

test("handleIssueStatusChanged returns null for non-matching statuses", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4478",
      newStatus: "in review",
      title: "FIFO: Why are deliveries getting assigned so many sub batches?",
    },
  });

  assert.equal(action, null);
});
