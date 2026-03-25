const { shouldMarkResearch, withResearchPrefix } = require('./logic');
const { updateIssueTitle } = require('./linearApi');

async function handleLinearWebhook(payload, options = {}) {
  const apiKey = options.apiKey || process.env.LINEAR_API_KEY;
  const fetchImpl = options.fetchImpl || fetch;

  if (!shouldMarkResearch(payload)) {
    return { changed: false, reason: 'not_research_status_change' };
  }

  const issueId = payload?.data?.id;
  const currentTitle = payload?.data?.title;

  if (!issueId) {
    return { changed: false, reason: 'missing_issue_id' };
  }

  const nextTitle = withResearchPrefix(currentTitle);
  if (nextTitle === (currentTitle || '').trim()) {
    return { changed: false, reason: 'title_already_prefixed' };
  }

  const success = await updateIssueTitle(issueId, nextTitle, apiKey, fetchImpl);
  return { changed: success, reason: success ? 'updated' : 'update_failed', title: nextTitle };
}

module.exports = {
  handleLinearWebhook,
};
