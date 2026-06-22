const CURSOR_RESEARCHING_PREFIX = 'Cursor researching';
const LINEAR_GRAPHQL_ENDPOINT = 'https://api.linear.app/graphql';

function compact(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function readPath(source, path) {
  return path.reduce((value, key) => {
    if (value == null || typeof value !== 'object') {
      return undefined;
    }

    return value[key];
  }, source);
}

function firstStringAtPath(source, paths) {
  for (const path of paths) {
    const value = compact(readPath(source, path));
    if (value) {
      return value;
    }
  }

  return '';
}

export function statusNameFromPayload(payload) {
  return firstStringAtPath(payload, [
    ['triggerContext', 'newStatus'],
    ['triggerContext', 'status'],
    ['data', 'node', 'state', 'name'],
    ['data', 'issue', 'state', 'name'],
    ['data', 'state', 'name'],
    ['issue', 'state', 'name'],
    ['state', 'name']
  ]);
}

export function isStatusChangedToResearch(payload) {
  const triggerName = compact(payload?.triggerContext?.trigger).toLowerCase();
  const actionName = compact(payload?.action).toLowerCase();
  const webhookType = compact(payload?.triggerContext?.webhookType).toLowerCase();
  const issueType = compact(payload?.type).toLowerCase();
  const statusName = statusNameFromPayload(payload).toLowerCase();

  const isIssueEvent = webhookType === 'issue' || issueType === 'issue';
  const isStatusChange = triggerName === 'status_changed' || actionName === 'update';

  return isIssueEvent && isStatusChange && statusName === 'to research';
}

export function titleWithCursorResearching(title) {
  const currentTitle = compact(title);
  if (!currentTitle) {
    return CURSOR_RESEARCHING_PREFIX;
  }

  if (currentTitle.toLowerCase().includes(CURSOR_RESEARCHING_PREFIX.toLowerCase())) {
    return currentTitle;
  }

  return `${CURSOR_RESEARCHING_PREFIX}: ${currentTitle}`;
}

export function issueIdFromPayload(payload) {
  return firstStringAtPath(payload, [
    ['triggerContext', 'id'],
    ['data', 'node', 'id'],
    ['data', 'issue', 'id'],
    ['issue', 'id'],
    ['id']
  ]);
}

export function issueTitleFromPayload(payload) {
  return firstStringAtPath(payload, [
    ['triggerContext', 'title'],
    ['data', 'node', 'title'],
    ['data', 'issue', 'title'],
    ['issue', 'title'],
    ['title']
  ]);
}

export function buildIssueTitleMutation(issueId, title) {
  return {
    query: `
      mutation UpdateIssueTitle($id: String!, $title: String!) {
        issueUpdate(id: $id, input: { title: $title }) {
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
      title
    }
  };
}

export async function updateIssueTitle({ issueId, title, apiKey, fetchImpl = globalThis.fetch }) {
  if (!apiKey) {
    throw new Error('LINEAR_API_KEY or LINEAR_API_TOKEN is required');
  }

  if (!issueId) {
    throw new Error('Linear issue id is required');
  }

  if (!title) {
    throw new Error('Linear issue title is required');
  }

  if (typeof fetchImpl !== 'function') {
    throw new Error('A fetch implementation is required');
  }

  const response = await fetchImpl(LINEAR_GRAPHQL_ENDPOINT, {
    method: 'POST',
    headers: {
      Authorization: apiKey,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(buildIssueTitleMutation(issueId, title))
  });

  const body = await response.json();
  if (!response.ok || body.errors?.length) {
    const errorMessage = body.errors?.map((error) => error.message).join('; ') || response.statusText;
    throw new Error(`Linear issue title update failed: ${errorMessage}`);
  }

  if (!body.data?.issueUpdate?.success) {
    throw new Error('Linear issue title update did not report success');
  }

  return body.data.issueUpdate.issue;
}

export async function handleLinearStatusChanged(payload, options = {}) {
  if (!isStatusChangedToResearch(payload)) {
    return {
      changed: false,
      reason: 'not_to_research_status_change'
    };
  }

  const issueId = issueIdFromPayload(payload);
  const nextTitle = titleWithCursorResearching(issueTitleFromPayload(payload));

  if (nextTitle === issueTitleFromPayload(payload)) {
    return {
      changed: false,
      reason: 'title_already_marked',
      issueId,
      title: nextTitle
    };
  }

  const issue = await updateIssueTitle({
    issueId,
    title: nextTitle,
    apiKey: options.apiKey ?? process.env.LINEAR_API_KEY ?? process.env.LINEAR_API_TOKEN,
    fetchImpl: options.fetchImpl
  });

  return {
    changed: true,
    issue
  };
}

async function readPayloadFromStdin() {
  const chunks = [];

  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }

  return Buffer.concat(chunks).toString('utf8');
}

async function readPayload() {
  const rawPayload =
    process.env.LINEAR_WEBHOOK_PAYLOAD ||
    process.env.CURSOR_AUTOMATION_TRIGGER ||
    process.env.TRIGGER_CONTEXT ||
    (await readPayloadFromStdin());

  if (!compact(rawPayload)) {
    throw new Error('No Linear webhook payload provided');
  }

  return JSON.parse(rawPayload);
}

export async function main() {
  const payload = await readPayload();
  const result = await handleLinearStatusChanged(payload);
  console.log(JSON.stringify(result, null, 2));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
