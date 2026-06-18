'use strict';

const {
  addCursorResearchingToTitle,
  handleIssueStatusChangedToResearch
} = require('./linearResearchTitle');

const LINEAR_API_URL = 'https://api.linear.app/graphql';

function createLinearClient({ apiKey, fetchImpl = globalThis.fetch } = {}) {
  if (!apiKey) {
    throw new Error('LINEAR_API_KEY is required to update Linear issues.');
  }

  if (typeof fetchImpl !== 'function') {
    throw new Error('A fetch implementation is required to call the Linear API.');
  }

  return {
    async updateIssueTitle(issueId, title) {
      const response = await fetchImpl(LINEAR_API_URL, {
        method: 'POST',
        headers: {
          Authorization: apiKey,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: `
            mutation UpdateIssueTitle($id: String!, $input: IssueUpdateInput!) {
              issueUpdate(id: $id, input: $input) {
                success
                issue {
                  id
                  title
                }
              }
            }
          `,
          variables: {
            id: issueId,
            input: { title }
          }
        })
      });

      const responseBody = await response.json().catch(() => null);

      if (!response.ok) {
        throw new Error(
          `Linear API request failed with ${response.status}: ${JSON.stringify(responseBody)}`
        );
      }

      if (responseBody && responseBody.errors && responseBody.errors.length > 0) {
        throw new Error(`Linear API returned errors: ${JSON.stringify(responseBody.errors)}`);
      }

      if (!responseBody || !responseBody.data || !responseBody.data.issueUpdate.success) {
        throw new Error(`Linear issue title update did not succeed: ${JSON.stringify(responseBody)}`);
      }

      return responseBody.data.issueUpdate.issue;
    }
  };
}

async function readStdin() {
  const chunks = [];

  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }

  return Buffer.concat(chunks).toString('utf8');
}

async function main() {
  const input = await readStdin();
  const payload = input.trim() ? JSON.parse(input) : {};
  const triggerContext = payload.triggerContext || payload;
  const linearClient = createLinearClient({ apiKey: process.env.LINEAR_API_KEY });
  const result = await handleIssueStatusChangedToResearch(triggerContext, linearClient);

  process.stdout.write(`${JSON.stringify(result)}\n`);
}

if (require.main === module) {
  main().catch((error) => {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  addCursorResearchingToTitle,
  createLinearClient,
  handleIssueStatusChangedToResearch
};
