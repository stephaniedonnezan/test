const { handleLinearWebhook } = require('./handler');

async function main() {
  const rawPayload = process.argv[2];
  if (!rawPayload) {
    throw new Error('Pass a JSON webhook payload as first argument');
  }

  const payload = JSON.parse(rawPayload);
  const result = await handleLinearWebhook(payload);
  console.log(JSON.stringify(result));
}

if (require.main === module) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}

module.exports = {
  main,
};
