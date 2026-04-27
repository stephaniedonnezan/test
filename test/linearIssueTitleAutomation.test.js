const test = require("node:test");
const assert = require("node:assert/strict");

const {
  RESEARCHING_TITLE_PREFIX,
  buildIssueTitleUpdate,
  hasResearchingPrefix,
  shouldApplyResearchingPrefix,
  withResearchingPrefix,
} = require("../src/linearIssueTitleAutomation");

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
      trigger: "STATUS CHANGED",
      newStatus: " To Research ",
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
      newStatus: "QA",
    }),
    false,
  );

  assert.equal(shouldApplyResearchingPrefix(null), false);
});

test("withResearchingPrefix adds the Cursor researching prefix", () => {
  assert.equal(
    withResearchingPrefix("Add UBA POS Pdf Preview"),
    `${RESEARCHING_TITLE_PREFIX}: Add UBA POS Pdf Preview`,
  );
});

test("withResearchingPrefix is idempotent for existing prefixes", () => {
  assert.equal(
    withResearchingPrefix("Cursor researching: Add UBA POS Pdf Preview"),
    "Cursor researching: Add UBA POS Pdf Preview",
  );

  assert.equal(
    withResearchingPrefix(" cursor researching Add UBA POS Pdf Preview "),
    "cursor researching Add UBA POS Pdf Preview",
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

test("buildIssueTitleUpdate returns an update for a matching automation payload", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Add UBA POS Pdf Preview",
      id: "POI-4201",
      url: "https://linear.app/atmen/issue/POI-4201/add-uba-pos-pdf-preview",
    },
  };

  assert.deepEqual(buildIssueTitleUpdate(payload), {
    action: "update_issue_title",
    issueId: "POI-4201",
    issueUrl: "https://linear.app/atmen/issue/POI-4201/add-uba-pos-pdf-preview",
    previousTitle: "Add UBA POS Pdf Preview",
    title: "Cursor researching: Add UBA POS Pdf Preview",
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
        newStatus: "QA",
        title: "Add UBA POS Pdf Preview",
        id: "POI-4201",
      },
    }),
    null,
  );

  assert.equal(
    buildIssueTitleUpdate({
      triggerContext: {
        trigger: "comment_created",
        newStatus: "to research",
        title: "Add UBA POS Pdf Preview",
        id: "POI-4201",
      },
    }),
    null,
  );
});
