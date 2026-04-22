import { updateIssueTitleWhenStatusIsToResearch } from "./linear-status-title-handler.mjs";

async function readInputPayload() {
  if (process.env.AUTOMATION_TRIGGER_INFO) {
    return JSON.parse(process.env.AUTOMATION_TRIGGER_INFO);
  }

  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }

  const stdinText = Buffer.concat(chunks).toString("utf8").trim();
  if (!stdinText) {
    return null;
  }

  return JSON.parse(stdinText);
}

async function main() {
  const payload = await readInputPayload();
  if (!payload) {
    throw new Error(
      "Missing automation payload. Provide AUTOMATION_TRIGGER_INFO or JSON on stdin.",
    );
  }

  const result = await updateIssueTitleWhenStatusIsToResearch({
    triggerInfo: payload,
    apiKey: process.env.LINEAR_API_KEY,
  });

  process.stdout.write(`${JSON.stringify(result)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
