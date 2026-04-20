import { getUpdatedIssueTitle } from "./linearIssueTitle.js";

/**
 * Generic entrypoint for automation triggers. Returns the action payload
 * for callers that execute API operations.
 */
export function handleIssueStatusChanged(event = {}) {
  const nextTitle = getUpdatedIssueTitle(event.triggerContext ?? {});
  if (!nextTitle) {
    return null;
  }

  return {
    action: "update_issue_title",
    issueId: event.triggerContext?.id ?? null,
    title: nextTitle,
  };
}
