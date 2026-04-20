import test from "node:test";
import assert from "node:assert/strict";

import {
  RESEARCH_PREFIX,
  buildResearchTitle,
  getUpdatedIssueTitle,
} from "./linearIssueTitle.js";

test("buildResearchTitle prefixes a plain title", () => {
  const title = "Add delivery destination address to export";
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
    newStatus: "to research",
    title: "Investigate upload behavior",
  });

  assert.equal(result, "Cursor researching: Investigate upload behavior");
});

test("getUpdatedIssueTitle matches status case-insensitively", () => {
  const result = getUpdatedIssueTitle({
    newStatus: "To Research",
    title: "Investigate upload behavior",
  });

  assert.equal(result, "Cursor researching: Investigate upload behavior");
});

test("getUpdatedIssueTitle returns null for other statuses", () => {
  const result = getUpdatedIssueTitle({
    newStatus: "In Progress",
    title: "Investigate upload behavior",
  });

  assert.equal(result, null);
});
