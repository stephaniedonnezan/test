const RESEARCH_PREFIX = "Cursor researching";

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
  const { newStatus, title } = triggerContext;
  if (normalize(newStatus) !== "to research") {
    return null;
  }

  return buildResearchTitle(title);
}

export { RESEARCH_PREFIX };
