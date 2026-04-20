import test from "node:test";
import assert from "node:assert/strict";

import {
  RESEARCH_PREFIX,
  buildResearchTitle,
  getUpdatedIssueTitle,
} from "./linearIssueTitle.js";

test("buildResearchTitle prefixes a plain title", () => {
  const title = "Add Info Snack Bar informing user of new release notes at new login";
  assert.equal(buildResearchTitle(title), `${RESEARCH_PREFIX}: ${title}`);
});

test("buildResearchTitle does not duplicate existing prefix", () => {
  const title = "Cursor researching: Existing title";
  assert.equal(buildResearchTitle(title), title);
});

test("buildResearchTitle handles empty titles", () => {
  assert.equal(buildResearchTitle("   "), RESEARCH_PREFIX);
});

test("getUpdatedIssueTitle prefixes title for to research status", () => {
  const result = getUpdatedIssueTitle({
    trigger: "status_changed",
    newStatus: "to research",
    title: "Investigate upload behavior",
  });

  assert.equal(result, "Cursor researching: Investigate upload behavior");
});

test("getUpdatedIssueTitle matches status case-insensitively", () => {
  const result = getUpdatedIssueTitle({
    trigger: "status_changed",
    newStatus: "To Research",
    title: "Investigate upload behavior",
  });

  assert.equal(result, "Cursor researching: Investigate upload behavior");
});

test("getUpdatedIssueTitle returns null for other statuses", () => {
  const result = getUpdatedIssueTitle({
    trigger: "status_changed",
    newStatus: "In Progress",
    title: "Investigate upload behavior",
  });

  assert.equal(result, null);
});

test("getUpdatedIssueTitle returns null for non status-change triggers", () => {
  const result = getUpdatedIssueTitle({
    trigger: "created",
    newStatus: "To Research",
    title: "Investigate upload behavior",
  });

  assert.equal(result, null);
});
