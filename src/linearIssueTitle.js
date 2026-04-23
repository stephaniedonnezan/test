const RESEARCH_PREFIX = "Cursor researching";

function normalizeStatus(status) {
  return String(status ?? "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function isResearchStatus(status) {
  return normalizeStatus(status) === "to research";
}

function hasResearchPrefix(title, prefix = RESEARCH_PREFIX) {
  return String(title ?? "")
    .trim()
    .toLowerCase()
    .startsWith(prefix.toLowerCase());
}

function updateIssueTitleForStatusChange({
  title,
  newStatus,
  prefix = RESEARCH_PREFIX,
}) {
  const currentTitle = String(title ?? "").trim();
  if (!isResearchStatus(newStatus)) {
    return currentTitle;
  }

  if (!currentTitle || hasResearchPrefix(currentTitle, prefix)) {
    return currentTitle;
  }

  return `${prefix} - ${currentTitle}`;
}

module.exports = {
  RESEARCH_PREFIX,
  normalizeStatus,
  isResearchStatus,
  hasResearchPrefix,
  updateIssueTitleForStatusChange,
};
