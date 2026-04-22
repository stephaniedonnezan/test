import test from "node:test";
import assert from "node:assert/strict";

import {
  RESEARCH_PREFIX,
  buildResearchTitle,
  getUpdatedIssueTitle,
} from "../src/linearIssueTitle.js";

test("buildResearchTitle prefixes a plain title", () => {
  const title = "Excel download button styling";
  assert.equal(buildResearchTitle(title), `${RESEARCH_PREFIX}: ${title}`);
});

test("buildResearchTitle does not duplicate existing prefix", () => {
  const title = "Cursor researching: Existing title";
  assert.equal(buildResearchTitle(title), title);
});

test("buildResearchTitle returns prefix for empty title", () => {
  assert.equal(buildResearchTitle("   "), RESEARCH_PREFIX);
});

test("getUpdatedIssueTitle returns prefixed title for to research", () => {
  const title = "Excel download button styling";
  assert.equal(
    getUpdatedIssueTitle({
      newStatus: "to research",
      title,
    }),
    `${RESEARCH_PREFIX}: ${title}`,
  );
});

test("getUpdatedIssueTitle matches status case-insensitively", () => {
  const title = "Excel download button styling";
  assert.equal(
    getUpdatedIssueTitle({
      newStatus: "To Research",
      title,
    }),
    `${RESEARCH_PREFIX}: ${title}`,
  );
});

test("getUpdatedIssueTitle returns null for other statuses", () => {
  assert.equal(
    getUpdatedIssueTitle({
      newStatus: "DEV",
      title: "Excel download button styling",
    }),
    null,
  );
});
