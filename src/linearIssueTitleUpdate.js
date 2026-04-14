const RESEARCHING_MARKER = "Cursor researching";
const STATUS_TO_RESEARCH = "to research";

function normalizeStatus(status) {
  return String(status || "").trim().toLowerCase();
}

function hasResearchingMarker(title) {
  return String(title || "")
    .toLowerCase()
    .includes(RESEARCHING_MARKER.toLowerCase());
}

function addResearchingMarkerToTitle(title) {
  const safeTitle = String(title || "").trim();
  if (!safeTitle) {
    return RESEARCHING_MARKER;
  }

  if (hasResearchingMarker(safeTitle)) {
    return safeTitle;
  }

  return `${RESEARCHING_MARKER} - ${safeTitle}`;
}

function getUpdatedIssueTitle(issueLike) {
  const payload = issueLike || {};
  const status = normalizeStatus(payload.newStatus ?? payload.status);
  const currentTitle = String(payload.title || "");

  if (status !== STATUS_TO_RESEARCH) {
    return currentTitle;
  }

  return addResearchingMarkerToTitle(currentTitle);
}

function getUpdatedTitleFromLinearAutomationPayload(payload) {
  const triggerContext = payload?.triggerContext || {};

  return getUpdatedIssueTitle({
    title: triggerContext.title,
    newStatus: triggerContext.newStatus,
  });
}

module.exports = {
  RESEARCHING_MARKER,
  STATUS_TO_RESEARCH,
  normalizeStatus,
  hasResearchingMarker,
  addResearchingMarkerToTitle,
  getUpdatedIssueTitle,
  getUpdatedTitleFromLinearAutomationPayload,
};
