"use strict";

const RESEARCH_STATUS = "to research";
const RESEARCH_PREFIX = "Cursor researching";

function isStatusToResearch(statusValue) {
  return typeof statusValue === "string" && statusValue.trim().toLowerCase() === RESEARCH_STATUS;
}

function hasResearchPrefix(title) {
  return typeof title === "string" && title.trim().toLowerCase().startsWith(RESEARCH_PREFIX.toLowerCase());
}

function getUpdatedIssueTitleForResearchStatus(payload) {
  const issueTitle = payload?.triggerContext?.title;
  const nextStatus = payload?.triggerContext?.newStatus;

  if (typeof issueTitle !== "string" || issueTitle.trim() === "") {
    return issueTitle;
  }

  if (!isStatusToResearch(nextStatus)) {
    return issueTitle;
  }

  if (hasResearchPrefix(issueTitle)) {
    return issueTitle;
  }

  return `${RESEARCH_PREFIX} ${issueTitle}`;
}

module.exports = {
  RESEARCH_PREFIX,
  getUpdatedIssueTitleForResearchStatus,
  hasResearchPrefix,
  isStatusToResearch,
};
