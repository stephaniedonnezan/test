import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4186",
      newStatus: "To Research",
      title: "Throw a 400 if the single delivery to close has any error",
    },
  });

  assert.deepEqual(result, {
    action: "update_issue_title",
    issueId: "POI-4186",
    title: "Cursor researching: Throw a 400 if the single delivery to close has any error",
  });
});

test("handleIssueStatusChanged returns null for non research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4186",
      newStatus: "In Progress",
      title: "Throw a 400 if the single delivery to close has any error",
    },
  });

  assert.equal(result, null);
});
