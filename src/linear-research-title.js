import { readFile } from 'node:fs/promises';
import process from 'node:process';
import { pathToFileURL } from 'node:url';

export const RESEARCHING_TITLE_MARKER = 'Cursor researching';
export const TARGET_STATUS = 'to research';
export const DEFAULT_LINEAR_GRAPHQL_ENDPOINT = 'https://api.linear.app/graphql';

function normalizeText(value) {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ');
}

function hasResearchingPrefix(title) {
  return /^\s*(?:\[\s*)?cursor\s+researching(?:\s*\])?(?:\s*[:|-])?/i.test(String(title ?? ''));
}

export function buildResearchingTitle(title) {
  const trimmedTitle = String(title ?? '').trim();

  if (!trimmedTitle) {
    return RESEARCHING_TITLE_MARKER;
  }

  if (hasResearchingPrefix(trimmedTitle)) {
    return trimmedTitle;
  }

  return `${RESEARCHING_TITLE_MARKER}: ${trimmedTitle}`;
}

export function extractStatusName(payload) {
  return (
    payload?.triggerContext?.newStatus ??
    payload?.triggerContext?.status ??
    payload?.data?.state?.name ??
    payload?.data?.status?.name ??
    payload?.data?.state ??
    payload?.state?.name ??
    payload?.status?.name ??
    payload?.status ??
    null
  );
}

export function isIssueStatusChange(payload) {
  const triggerContext = payload?.triggerContext;

  if (triggerContext) {
    return (
      normalizeText(triggerContext.triggerType) === 'linear' &&
      normalizeText(triggerContext.webhookType) === 'issue' &&
      normalizeText(triggerContext.trigger) === 'status changed'
    );
  }

  if (payload?.type && normalizeText(payload.type) !== 'issue') {
    return false;
  }

  if (normalizeText(payload?.action) !== 'update') {
    return false;
  }

  return Boolean(
    payload?.updatedFrom?.stateId ??
      payload?.updatedFrom?.state ??
      payload?.updatedFrom?.status ??
      payload?.updatedFrom?.statusId
  );
}

export function shouldMarkIssueAsResearching(payload) {
  return isIssueStatusChange(payload) && normalizeText(extractStatusName(payload)) === TARGET_STATUS;
}

export function extractIssueReference(payload) {
  const triggerContext = payload?.triggerContext;
  const data = payload?.data;

  return {
    id:
      triggerContext?.issueId ??
      triggerContext?.linearIssueId ??
      triggerContext?.id ??
      data?.id ??
      payload?.issueId ??
      payload?.id ??
      null,
    title: triggerContext?.title ?? data?.title ?? payload?.title ?? null,
    url: triggerContext?.url ?? data?.url ?? payload?.url ?? null,
  };
}

export function createLinearClient({
  apiKey,
  endpoint = DEFAULT_LINEAR_GRAPHQL_ENDPOINT,
  fetchImpl = globalThis.fetch,
} = {}) {
  if (!apiKey) {
    throw new Error('LINEAR_API_KEY or LINEAR_TOKEN is required to update Linear issue titles.');
  }

  if (!fetchImpl) {
    throw new Error('A fetch implementation is required to call the Linear API.');
  }

  async function graphql(query, variables) {
    const response = await fetchImpl(endpoint, {
      method: 'POST',
      headers: {
        Authorization: apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, variables }),
    });

    if (!response.ok) {
      const responseBody = await response.text();
      throw new Error(`Linear API request failed with ${response.status}: ${responseBody}`);
    }

    const body = await response.json();

    if (body.errors?.length) {
      const message = body.errors.map((error) => error.message).join('; ');
      throw new Error(`Linear API returned errors: ${message}`);
    }

    return body.data;
  }

  return {
    async getIssue(issueIdOrIdentifier) {
      const data = await graphql(
        `query IssueForResearchTitle($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
          }
        }`,
        { id: issueIdOrIdentifier }
      );

      if (!data?.issue) {
        throw new Error(`Linear issue not found: ${issueIdOrIdentifier}`);
      }

      return data.issue;
    },

    async updateIssueTitle(issueId, title) {
      const data = await graphql(
        `mutation UpdateIssueResearchTitle($id: String!, $title: String!) {
          issueUpdate(id: $id, input: { title: $title }) {
            success
            issue {
              id
              identifier
              title
            }
          }
        }`,
        { id: issueId, title }
      );

      if (!data?.issueUpdate?.success) {
        throw new Error(`Linear issue title update failed for ${issueId}`);
      }

      return data.issueUpdate.issue;
    },
  };
}

export async function markResearchingTitleForPayload(payload, options = {}) {
  const issueReference = extractIssueReference(payload);
  const detectedStatus = extractStatusName(payload);

  if (!shouldMarkIssueAsResearching(payload)) {
    return {
      updated: false,
      reason: 'not-to-research-status-change',
      detectedStatus,
      issue: issueReference,
    };
  }

  if (!issueReference.id) {
    throw new Error('Linear issue id or identifier is required to update the title.');
  }

  if (options.dryRun) {
    return {
      updated: false,
      reason: 'dry-run',
      title: buildResearchingTitle(issueReference.title),
      issue: issueReference,
    };
  }

  const client =
    options.linearClient ??
    createLinearClient({
      apiKey: options.apiKey ?? process.env.LINEAR_API_KEY ?? process.env.LINEAR_TOKEN,
      endpoint: options.endpoint,
      fetchImpl: options.fetchImpl,
    });

  const issue = await client.getIssue(issueReference.id);
  const nextTitle = buildResearchingTitle(issue.title ?? issueReference.title);

  if (nextTitle === issue.title) {
    return {
      updated: false,
      reason: 'already-marked',
      title: issue.title,
      issue,
    };
  }

  const updatedIssue = await client.updateIssueTitle(issue.id, nextTitle);

  return {
    updated: true,
    previousTitle: issue.title,
    title: updatedIssue.title,
    issue: updatedIssue,
  };
}

async function readStdin() {
  let body = '';
  process.stdin.setEncoding('utf8');

  for await (const chunk of process.stdin) {
    body += chunk;
  }

  return body;
}

async function readPayload(argv) {
  const payloadFlagIndex = argv.indexOf('--payload');

  if (payloadFlagIndex !== -1) {
    const payloadPath = argv[payloadFlagIndex + 1];

    if (!payloadPath) {
      throw new Error('--payload requires a path to a JSON payload file.');
    }

    return JSON.parse(await readFile(payloadPath, 'utf8'));
  }

  const stdinBody = await readStdin();

  if (!stdinBody.trim()) {
    throw new Error('Provide a Linear webhook payload on stdin or via --payload <file>.');
  }

  return JSON.parse(stdinBody);
}

async function main(argv = process.argv.slice(2)) {
  const payload = await readPayload(argv);
  const result = await markResearchingTitleForPayload(payload, {
    dryRun: argv.includes('--dry-run'),
  });

  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    process.stderr.write(`${error.stack ?? error.message}\n`);
    process.exitCode = 1;
  });
}
