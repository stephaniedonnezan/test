"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  RESEARCHING_TITLE_PREFIX,
  buildIssueTitleUpdate,
  hasResearchingPrefix,
  normalizeStatus,
  normalizeTrigger,
  shouldApplyResearchingPrefix,
  withResearchingPrefix,
} = require("../src/linearIssueTitleAutomation");

test("normalizeStatus matches Linear to research status variants", () => {
  assert.equal(normalizeStatus(" To Research "), "to research");
  assert.equal(normalizeStatus("to_research"), "to research");
  assert.equal(normalizeStatus("to-research"), "to research");
});

test("normalizeTrigger matches status changed variants", () => {
  assert.equal(normalizeTrigger("status_changed"), "status_changed");
  assert.equal(normalizeTrigger("STATUS CHANGED"), "status_changed");
  assert.equal(normalizeTrigger("status-changed"), "status_changed");
});

test("shouldApplyResearchingPrefix matches status_changed to to research", () => {
  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status_changed",
      newStatus: "to research",
    }),
    true,
  );

  assert.equal(
    shouldApplyResearchingPrefix({
      triggerContext: {
        trigger: "STATUS CHANGED",
        newStatus: " To Research ",
      },
    }),
    true,
  );

  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status-changed",
      status: "to_research",
    }),
    true,
  );
});

test("shouldApplyResearchingPrefix rejects unrelated triggers and statuses", () => {
  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "created",
      newStatus: "to research",
    }),
    false,
  );

  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status_changed",
      newStatus: "Done",
    }),
    false,
  );

  assert.equal(shouldApplyResearchingPrefix(null), false);
});

test("withResearchingPrefix adds the Cursor researching prefix", () => {
  assert.equal(
    withResearchingPrefix("[][Dev] - PoS document handling"),
    `${RESEARCHING_TITLE_PREFIX}: [][Dev] - PoS document handling`,
  );
});

test("withResearchingPrefix is idempotent for existing prefixes", () => {
  assert.equal(
    withResearchingPrefix("Cursor researching: [][Dev] - PoS document handling"),
    "Cursor researching: [][Dev] - PoS document handling",
  );

  assert.equal(
    withResearchingPrefix(" cursor researching [][Dev] - PoS document handling "),
    "cursor researching [][Dev] - PoS document handling",
  );
});

test("withResearchingPrefix handles blank titles", () => {
  assert.equal(withResearchingPrefix("   "), RESEARCHING_TITLE_PREFIX);
  assert.equal(withResearchingPrefix(undefined), RESEARCHING_TITLE_PREFIX);
});

test("hasResearchingPrefix is case-insensitive and title-start anchored", () => {
  assert.equal(hasResearchingPrefix("cursor researching: test"), true);
  assert.equal(hasResearchingPrefix("  CURSOR RESEARCHING test"), true);
  assert.equal(hasResearchingPrefix("test Cursor researching"), false);
});

test("buildIssueTitleUpdate returns an update for matching automation payload", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "[][Dev] - PoS document handling",
      id: "POI-4206",
      url: "https://linear.app/atmen/issue/POI-4206/dev-pos-document-handling",
    },
  };

  assert.deepEqual(buildIssueTitleUpdate(payload), {
    action: "update_issue_title",
    issueId: "POI-4206",
    issueUrl: "https://linear.app/atmen/issue/POI-4206/dev-pos-document-handling",
    previousTitle: "[][Dev] - PoS document handling",
    title: "Cursor researching: [][Dev] - PoS document handling",
  });
});

test("buildIssueTitleUpdate accepts a flat trigger context", () => {
  assert.deepEqual(
    buildIssueTitleUpdate({
      trigger: "status_changed",
      newStatus: "to research",
      title: "Research this issue",
      id: "POI-1",
    }),
    {
      action: "update_issue_title",
      issueId: "POI-1",
      issueUrl: undefined,
      previousTitle: "Research this issue",
      title: "Cursor researching: Research this issue",
    },
  );
});

test("buildIssueTitleUpdate returns null when no title change is needed", () => {
  assert.equal(
    buildIssueTitleUpdate({
      triggerContext: {
        trigger: "status_changed",
        newStatus: "to research",
        title: "Cursor researching: Existing",
        id: "POI-2",
      },
    }),
    null,
  );
});

test("buildIssueTitleUpdate returns null for unrelated events", () => {
  assert.equal(
    buildIssueTitleUpdate({
      triggerContext: {
        trigger: "status_changed",
        newStatus: "Done",
        title: "[][Dev] - PoS document handling",
        id: "POI-4206",
      },
    }),
    null,
  );

  assert.equal(
    buildIssueTitleUpdate({
      triggerContext: {
        trigger: "comment_created",
        newStatus: "to research",
        title: "[][Dev] - PoS document handling",
        id: "POI-4206",
      },
    }),
    null,
  );
});
