async function linearGraphQLRequest(query, variables, apiKey, fetchImpl = fetch) {
  if (!apiKey) {
    throw new Error('Missing LINEAR_API_KEY');
  }

  const response = await fetchImpl('https://api.linear.app/graphql', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: apiKey,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Linear API request failed: ${response.status} ${body}`);
  }

  const data = await response.json();
  if (data.errors && data.errors.length > 0) {
    throw new Error(`Linear API errors: ${JSON.stringify(data.errors)}`);
  }

  return data.data;
}

async function updateIssueTitle(issueId, title, apiKey, fetchImpl = fetch) {
  const mutation = `
    mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) {
        success
      }
    }
  `;

  const result = await linearGraphQLRequest(
    mutation,
    { id: issueId, input: { title } },
    apiKey,
    fetchImpl
  );

  return result?.issueUpdate?.success === true;
}

module.exports = {
  linearGraphQLRequest,
  updateIssueTitle,
};
