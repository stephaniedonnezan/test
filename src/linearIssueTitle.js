const RESEARCH_PREFIX = "Cursor researching";
const RESEARCH_STATUS = "to research";

function normalize(value) {
  return String(value ?? "").trim().toLowerCase();
}

function hasResearchPrefix(title) {
  return normalize(title).startsWith(normalize(RESEARCH_PREFIX));
}

export function buildResearchTitle(title) {
  const trimmedTitle = String(title ?? "").trim();
  if (!trimmedTitle) {
    return RESEARCH_PREFIX;
  }

  if (hasResearchPrefix(trimmedTitle)) {
    return trimmedTitle;
  }

  return `${RESEARCH_PREFIX}: ${trimmedTitle}`;
}

export function getUpdatedIssueTitle(triggerContext = {}) {
  if (normalize(triggerContext.newStatus) !== RESEARCH_STATUS) {
    return null;
  }

  return buildResearchTitle(triggerContext.title);
}

export { RESEARCH_PREFIX, RESEARCH_STATUS, hasResearchPrefix };
