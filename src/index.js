const { handleLinearWebhook } = require('./handler');

async function main() {
  const raw = process.argv[2];
  if (!raw) {
    throw new Error('Pass a JSON webhook payload as first argument');
  }

  const payload = JSON.parse(raw);
  const result = await handleLinearWebhook(payload);
  console.log(JSON.stringify(result));
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err.message);
    process.exit(1);
  });
}

module.exports = {
  main,
};
