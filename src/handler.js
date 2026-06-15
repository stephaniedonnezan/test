const { updateIssueTitle } = require('./linearApi');
const { buildIssueTitleUpdate } = require('./logic');

async function handleLinearWebhook(payload, options = {}) {
  const titleUpdate = buildIssueTitleUpdate(payload);
  if (!titleUpdate) {
    return { changed: false, reason: 'no_title_update_needed' };
  }

  const apiKey = options.apiKey || process.env.LINEAR_API_KEY;
  const fetchImpl = options.fetchImpl || fetch;
  const success = await updateIssueTitle(titleUpdate.issueId, titleUpdate.title, apiKey, fetchImpl);

  return {
    changed: success,
    reason: success ? 'updated' : 'update_failed',
    ...titleUpdate,
  };
}

module.exports = {
  handleLinearWebhook,
};
