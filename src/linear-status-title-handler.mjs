const CURSOR_RESEARCHING_PREFIX = "Cursor researching";

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

export function shouldAddCursorResearchingToTitle(triggerInfo) {
  const triggerContext = triggerInfo?.triggerContext;

  if (!triggerContext) {
    return false;
  }

  const isStatusChange = normalize(triggerContext.trigger) === "status_changed";
  const isToResearch = normalize(triggerContext.newStatus) === "to research";

  return isStatusChange && isToResearch;
}

export function buildCursorResearchingTitle(title) {
  const rawTitle = String(title || "").trim();

  if (!rawTitle) {
    return CURSOR_RESEARCHING_PREFIX;
  }

  if (rawTitle.startsWith(CURSOR_RESEARCHING_PREFIX)) {
    return rawTitle;
  }

  return `${CURSOR_RESEARCHING_PREFIX} - ${rawTitle}`;
}

async function linearGraphqlRequest({ apiKey, query, variables, fetchImpl }) {
  const response = await fetchImpl("https://api.linear.app/graphql", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: apiKey,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    const bodyText = await response.text();
    throw new Error(`Linear request failed (${response.status}): ${bodyText}`);
  }

  return response.json();
}

export async function updateIssueTitleWhenStatusIsToResearch({
  triggerInfo,
  apiKey,
  fetchImpl = fetch,
}) {
  if (!shouldAddCursorResearchingToTitle(triggerInfo)) {
    return {
      updated: false,
      reason: "status_did_not_match_to_research",
    };
  }

  const issueId = triggerInfo?.triggerContext?.id;
  const currentTitle = triggerInfo?.triggerContext?.title;

  if (!issueId) {
    throw new Error("Missing issue id in trigger payload.");
  }

  if (!apiKey) {
    throw new Error("LINEAR_API_KEY is required to update issue title.");
  }

  const updatedTitle = buildCursorResearchingTitle(currentTitle);

  if (updatedTitle === String(currentTitle || "").trim()) {
    return {
      updated: false,
      reason: "already_prefixed",
      title: updatedTitle,
    };
  }

  const mutation = `
    mutation UpdateIssueTitle($id: String!, $title: String!) {
      issueUpdate(id: $id, input: { title: $title }) {
        success
      }
    }
  `;

  const responseJson = await linearGraphqlRequest({
    apiKey,
    query: mutation,
    variables: {
      id: issueId,
      title: updatedTitle,
    },
    fetchImpl,
  });

  if (responseJson?.errors?.length) {
    throw new Error(`Linear returned errors: ${JSON.stringify(responseJson.errors)}`);
  }

  const success = Boolean(responseJson?.data?.issueUpdate?.success);
  if (!success) {
    throw new Error("Linear did not confirm issue update success.");
  }

  return {
    updated: true,
    issueId,
    title: updatedTitle,
  };
}

export const constants = {
  CURSOR_RESEARCHING_PREFIX,
};
