"use strict";

const CURSOR_RESEARCHING_TAG = "Cursor researching";

function normalizeStatus(status) {
  return typeof status === "string" ? status.trim().toLowerCase() : "";
}

function hasCursorResearchingTag(title) {
  return typeof title === "string" && /\bcursor researching\b/i.test(title);
}

function withCursorResearchingTag(title) {
  const normalizedTitle = typeof title === "string" ? title.trim() : "";

  if (hasCursorResearchingTag(normalizedTitle)) {
    return normalizedTitle;
  }

  if (!normalizedTitle) {
    return CURSOR_RESEARCHING_TAG;
  }

  return `${CURSOR_RESEARCHING_TAG} - ${normalizedTitle}`;
}

function ensureCursorResearchingPrefix(title, newStatus) {
  if (normalizeStatus(newStatus) !== "to research") {
    return typeof title === "string" ? title : "";
  }

  return withCursorResearchingTag(title);
}

function updateIssueTitleForStatus({ title, newStatus } = {}) {
  return ensureCursorResearchingPrefix(title, newStatus);
}

module.exports = {
  CURSOR_RESEARCHING_TAG,
  ensureCursorResearchingPrefix,
  hasCursorResearchingTag,
  normalizeStatus,
  updateIssueTitleForStatus,
  withCursorResearchingTag,
};
