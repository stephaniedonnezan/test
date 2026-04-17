import test from "node:test";
import assert from "node:assert/strict";

import {
  RESEARCH_PREFIX,
  buildResearchTitle,
  getUpdatedIssueTitle,
} from "./linearIssueTitle.js";

test("buildResearchTitle prefixes a plain title", () => {
  const title = "Prevent closing in Closing view when there are errors";
  assert.equal(buildResearchTitle(title), `${RESEARCH_PREFIX}: ${title}`);
});

test("buildResearchTitle does not duplicate an existing prefix", () => {
  const title = "Cursor researching: Existing title";
  assert.equal(buildResearchTitle(title), title);
});

test("buildResearchTitle handles empty titles", () => {
  assert.equal(buildResearchTitle("   "), RESEARCH_PREFIX);
});

test("getUpdatedIssueTitle returns prefixed title for 'to research' status", () => {
  const result = getUpdatedIssueTitle({
    newStatus: "to research",
    title: "Investigate automation behavior",
  });
  assert.equal(result, "Cursor researching: Investigate automation behavior");
});

test("getUpdatedIssueTitle is case-insensitive for status matching", () => {
  const result = getUpdatedIssueTitle({
    newStatus: "To Research",
    title: "Investigate automation behavior",
  });
  assert.equal(result, "Cursor researching: Investigate automation behavior");
});

test("getUpdatedIssueTitle returns null for unrelated statuses", () => {
  const result = getUpdatedIssueTitle({
    newStatus: "DEV",
    title: "Investigate automation behavior",
  });
  assert.equal(result, null);
});
