const RESEARCH_PREFIX = "Cursor researching";

/**
 * Build an updated issue title based on status changes.
 * Adds a research prefix when the status moves to "to research".
 *
 * @param {Object} params
 * @param {string} params.title - Existing issue title.
 * @param {string} params.newStatus - New status value from automation trigger.
 * @returns {string}
 */
function buildIssueTitleForStatusChange({ title, newStatus }) {
  if (typeof title !== "string" || title.trim() === "") {
    throw new Error("title must be a non-empty string");
  }

  if (typeof newStatus !== "string") {
    return title;
  }

  const normalizedStatus = newStatus.trim().toLowerCase();
  if (normalizedStatus !== "to research") {
    return title;
  }

  const normalizedTitle = title.trim();
  const normalizedPrefix = RESEARCH_PREFIX.toLowerCase();
  if (normalizedTitle.toLowerCase().startsWith(normalizedPrefix)) {
    return normalizedTitle;
  }

  return `${RESEARCH_PREFIX}: ${normalizedTitle}`;
}

module.exports = {
  RESEARCH_PREFIX,
  buildIssueTitleForStatusChange,
};
