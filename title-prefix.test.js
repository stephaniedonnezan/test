const test = require("node:test");
const assert = require("node:assert/strict");

const {
  RESEARCHING_PREFIX,
  buildResearchingTitle,
  getIssueTitleUpdateFromAutomationEvent,
  getUpdatedTitleForStatusChange,
  hasResearchingPrefix,
} = require("./title-prefix");

test("adds prefix when status changes to to research", () => {
  const result = getUpdatedTitleForStatusChange({
    newStatus: "to research",
    title: "Trading delivery bug",
  });

  assert.equal(result.shouldUpdate, true);
  assert.equal(result.title, `${RESEARCHING_PREFIX}: Trading delivery bug`);
});

test("does not duplicate existing prefix", () => {
  const prefixedTitle = `${RESEARCHING_PREFIX}: Trading delivery bug`;
  const result = getUpdatedTitleForStatusChange({
    newStatus: "to research",
    title: prefixedTitle,
  });

  assert.equal(result.shouldUpdate, false);
  assert.equal(result.title, prefixedTitle);
});

test("does not update for other statuses", () => {
  const result = getUpdatedTitleForStatusChange({
    newStatus: "dev",
    title: "Trading delivery bug",
  });

  assert.deepEqual(result, {
    shouldUpdate: false,
    title: "Trading delivery bug",
  });
});

test("automation event parser only reacts to issue status_changed trigger", () => {
  const result = getIssueTitleUpdateFromAutomationEvent({
    triggerContext: {
      trigger: "status_changed",
      webhookType: "issue",
      newStatus: "to research",
      title: "Trading delivery bug",
    },
  });

  assert.equal(result.shouldUpdate, true);
  assert.equal(result.title, `${RESEARCHING_PREFIX}: Trading delivery bug`);
});

test("ignores non-status-changed events", () => {
  const result = getIssueTitleUpdateFromAutomationEvent({
    triggerContext: {
      trigger: "comment_created",
      webhookType: "issue",
      newStatus: "to research",
      title: "Trading delivery bug",
    },
  });

  assert.deepEqual(result, {
    shouldUpdate: false,
    title: "Trading delivery bug",
  });
});

test("hasResearchingPrefix handles direct prefix and separators", () => {
  assert.equal(hasResearchingPrefix("Cursor researching"), true);
  assert.equal(hasResearchingPrefix("Cursor researching - Trading delivery bug"), true);
  assert.equal(hasResearchingPrefix("Cursor researching: Trading delivery bug"), true);
  assert.equal(hasResearchingPrefix("Trading delivery bug"), false);
});

test("buildResearchingTitle handles empty titles", () => {
  assert.equal(buildResearchingTitle(""), RESEARCHING_PREFIX);
});
