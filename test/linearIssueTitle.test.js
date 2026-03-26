"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  getUpdatedIssueTitleForResearchStatus,
} = require("../src/linearIssueTitle");

test("prefixes title when status changes to 'to research'", () => {
  const payload = {
    triggerContext: {
      newStatus: "to research",
      title: "Change pre-push hook behavior",
    },
  };

  const result = getUpdatedIssueTitleForResearchStatus(payload);

  assert.equal(result, "Cursor researching Change pre-push hook behavior");
});

test("matches 'to research' status case-insensitively", () => {
  const payload = {
    triggerContext: {
      newStatus: "To Research",
      title: "Optimize nx affected usage",
    },
  };

  const result = getUpdatedIssueTitleForResearchStatus(payload);

  assert.equal(result, "Cursor researching Optimize nx affected usage");
});

test("does not duplicate prefix when title already has it", () => {
  const payload = {
    triggerContext: {
      newStatus: "to research",
      title: "Cursor researching Optimize nx affected usage",
    },
  };

  const result = getUpdatedIssueTitleForResearchStatus(payload);

  assert.equal(result, "Cursor researching Optimize nx affected usage");
});

test("leaves title unchanged for non-research statuses", () => {
  const payload = {
    triggerContext: {
      newStatus: "In Review",
      title: "Change pre-push hook behavior",
    },
  };

  const result = getUpdatedIssueTitleForResearchStatus(payload);

  assert.equal(result, "Change pre-push hook behavior");
});
