import assert from "node:assert/strict";
import test from "node:test";

import {
  buildCursorResearchingTitle,
  shouldAddCursorResearchingToTitle,
  updateIssueTitleWhenStatusIsToResearch,
} from "../src/linear-status-title-handler.mjs";

test("shouldAddCursorResearchingToTitle only returns true for status_changed to to research", () => {
  assert.equal(
    shouldAddCursorResearchingToTitle({
      triggerContext: {
        trigger: "status_changed",
        newStatus: "to research",
      },
    }),
    true,
  );

  assert.equal(
    shouldAddCursorResearchingToTitle({
      triggerContext: {
        trigger: "status_changed",
        newStatus: "triage",
      },
    }),
    false,
  );

  assert.equal(
    shouldAddCursorResearchingToTitle({
      triggerContext: {
        trigger: "comment_added",
        newStatus: "to research",
      },
    }),
    false,
  );
});

test("buildCursorResearchingTitle prefixes title once", () => {
  assert.equal(
    buildCursorResearchingTitle("Issue title"),
    "Cursor researching - Issue title",
  );

  assert.equal(
    buildCursorResearchingTitle("Cursor researching - Existing"),
    "Cursor researching - Existing",
  );
});

test("updateIssueTitleWhenStatusIsToResearch does not update for non matching status", async () => {
  const result = await updateIssueTitleWhenStatusIsToResearch({
    triggerInfo: {
      triggerContext: {
        trigger: "status_changed",
        newStatus: "triage",
      },
    },
    apiKey: "key",
    fetchImpl: async () => {
      throw new Error("fetch should not be called");
    },
  });

  assert.deepEqual(result, {
    updated: false,
    reason: "status_did_not_match_to_research",
  });
});

test("updateIssueTitleWhenStatusIsToResearch updates title when matching", async () => {
  let requestBody;
  const fakeFetch = async (_url, options) => {
    requestBody = JSON.parse(options.body);
    return {
      ok: true,
      json: async () => ({
        data: {
          issueUpdate: {
            success: true,
          },
        },
      }),
    };
  };

  const result = await updateIssueTitleWhenStatusIsToResearch({
    triggerInfo: {
      triggerContext: {
        trigger: "status_changed",
        newStatus: "to research",
        id: "POI-4530",
        title: "Trader Site and Producer Site",
      },
    },
    apiKey: "key",
    fetchImpl: fakeFetch,
  });

  assert.equal(result.updated, true);
  assert.equal(result.issueId, "POI-4530");
  assert.equal(
    result.title,
    "Cursor researching - Trader Site and Producer Site",
  );
  assert.equal(
    requestBody.variables.title,
    "Cursor researching - Trader Site and Producer Site",
  );
});
