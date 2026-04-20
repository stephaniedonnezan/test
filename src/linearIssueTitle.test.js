import test from "node:test";
import assert from "node:assert/strict";

import {
  RESEARCH_PREFIX,
  buildResearchTitle,
  getUpdatedIssueTitle,
} from "./linearIssueTitle.js";

test("buildResearchTitle prefixes a plain title", () => {
  const title = "Throw a 400 if the single delivery to close has any error";
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
    title: "Throw a 400 if the single delivery to close has any error",
  });

  assert.equal(
    result,
    "Cursor researching: Throw a 400 if the single delivery to close has any error",
  );
});

test("getUpdatedIssueTitle matches status case-insensitively", () => {
  const result = getUpdatedIssueTitle({
    newStatus: "To Research",
    title: "Throw a 400 if the single delivery to close has any error",
  });

  assert.equal(
    result,
    "Cursor researching: Throw a 400 if the single delivery to close has any error",
  );
});

test("getUpdatedIssueTitle returns null for other statuses", () => {
  const result = getUpdatedIssueTitle({
    newStatus: "In Progress",
    title: "Throw a 400 if the single delivery to close has any error",
  });

  assert.equal(result, null);
});
