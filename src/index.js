import { getUpdatedIssueTitle } from "./linearIssueTitle.js";

/**
 * Generic entrypoint for automation triggers. Returns a minimal action
 * payload for callers that perform API operations.
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
