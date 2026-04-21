import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4510",
      newStatus: "To Research",
      title: "Credit transfer within Atmen platform - not compliant with RED",
    },
  });

  assert.deepEqual(result, {
    action: "update_issue_title",
    issueId: "POI-4510",
    title:
      "Cursor researching: Credit transfer within Atmen platform - not compliant with RED",
  });
});

test("handleIssueStatusChanged returns null for non research status", () => {
  const result = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4510",
      newStatus: "In Progress",
      title: "Credit transfer within Atmen platform - not compliant with RED",
    },
  });

  assert.equal(result, null);
});
