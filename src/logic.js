const RESEARCH_PREFIX = 'Cursor researching';

function normalizeStatusName(statusName) {
  if (!statusName || typeof statusName !== 'string') {
    return '';
  }

  return statusName.trim().toLowerCase();
}

function shouldMarkResearch(event) {
  if (!event || event.type !== 'Issue') {
    return false;
  }

  if (event.action !== 'update') {
    return false;
  }

  const changedFrom = normalizeStatusName(event?.data?.previous?.state?.name);
  const changedTo = normalizeStatusName(event?.data?.state?.name);

  // Only act when transitioning into "to research".
  return changedTo === 'to research' && changedFrom !== changedTo;
}

function withResearchPrefix(title) {
  const safeTitle = (title || '').trim();
  if (!safeTitle) {
    return RESEARCH_PREFIX;
  }

  if (safeTitle.toLowerCase().startsWith(RESEARCH_PREFIX.toLowerCase())) {
    return safeTitle;
  }

  return `${RESEARCH_PREFIX}: ${safeTitle}`;
}

module.exports = {
  RESEARCH_PREFIX,
  shouldMarkResearch,
  withResearchPrefix,
};
