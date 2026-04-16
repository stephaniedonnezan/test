"use strict";

const { ensureCursorResearchingPrefix } = require("./issueTitle");

function parseNewStatus(triggerContext = {}) {
  const rawStatus = triggerContext.newStatus ?? triggerContext.status ?? "";
  return String(rawStatus).trim().toLowerCase();
}

function getCurrentTitle(triggerContext = {}) {
  return String(triggerContext.title ?? "");
}

function buildUpdatedIssueTitleFromStatusChangePayload(payload = {}) {
  const triggerContext = payload.triggerContext ?? {};
  const status = parseNewStatus(triggerContext);
  const currentTitle = getCurrentTitle(triggerContext);

  if (status !== "to research") {
    return currentTitle;
  }

  return ensureCursorResearchingPrefix(currentTitle, status);
}

module.exports = {
  buildUpdatedIssueTitleFromStatusChangePayload,
  parseNewStatus,
  getCurrentTitle,
};
