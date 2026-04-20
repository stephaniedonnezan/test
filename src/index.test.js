import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4397",
      newStatus: "To Research",
      title: "Investigate if adding origin address is possible",
    },
  });

  assert.deepEqual(result, {
    action: "update_issue_title",
    issueId: "POI-4397",
    title: "Cursor researching: Investigate if adding origin address is possible",
  });
});

test("handleIssueStatusChanged returns null for non research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4397",
      newStatus: "QA",
      title: "Investigate if adding origin address is possible",
    },
  });

  assert.equal(result, null);
});
