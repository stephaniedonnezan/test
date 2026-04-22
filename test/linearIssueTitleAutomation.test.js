const test = require("node:test");
const assert = require("node:assert/strict");

const {
  RESEARCHING_TITLE_PREFIX,
  buildIssueTitleUpdate,
  hasResearchingPrefix,
  shouldApplyResearchingPrefix,
  withResearchingPrefix,
} = require("../src/linearIssueTitleAutomation");

test("shouldApplyResearchingPrefix only returns true for status_changed to 'to research'", () => {
  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status_changed",
      newStatus: "to research",
    }),
    true,
  );

  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status_changed",
      newStatus: "To Research",
    }),
    true,
  );

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
      newStatus: "in progress",
    }),
    false,
  );
});

test("withResearchingPrefix adds prefix and stays idempotent", () => {
  assert.equal(
    withResearchingPrefix("Production build is still in Strict mode"),
    `${RESEARCHING_TITLE_PREFIX}: Production build is still in Strict mode`,
  );

  assert.equal(
    withResearchingPrefix("Cursor researching: Existing"),
    "Cursor researching: Existing",
  );
});

test("hasResearchingPrefix handles case-insensitive values", () => {
  assert.equal(hasResearchingPrefix("cursor researching: test"), true);
  assert.equal(hasResearchingPrefix("Cursor researching test"), true);
  assert.equal(hasResearchingPrefix("Researching cursor test"), false);
});

test("buildIssueTitleUpdate returns update payload for matching event", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Production build is still in Strict mode",
      id: "POI-2796",
    },
  };

  assert.deepEqual(buildIssueTitleUpdate(payload), {
    issueId: "POI-2796",
    previousTitle: "Production build is still in Strict mode",
    nextTitle: "Cursor researching: Production build is still in Strict mode",
  });
});

test("buildIssueTitleUpdate returns null when title already prefixed", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Cursor researching: Production build is still in Strict mode",
      id: "POI-2796",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});

test("buildIssueTitleUpdate returns null for unrelated status", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "in progress",
      title: "Production build is still in Strict mode",
      id: "POI-2796",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});
