import { makeClient, DEV_AGENT_NAME } from './agent.js';

// Isolated deepwiki check -- no sandbox, no file task -- to conserve Gemini free-tier
// quota while isolating whether the earlier connection failure was transient.

const client = makeClient();

async function main() {
  const { data: session } = await client.sessions.create({ agent: { name: DEV_AGENT_NAME } });
  console.log('session id:', session.id);

  const stream = await client.sessions.createTurnStream(session.id, {
    input: [
      {
        type: 'user.message',
        content: 'Use deepwiki to tell me in one sentence what the truefoundry/trueforge repository is for.',
      },
    ],
  });

  for await (const { data: event } of stream.withMetadata()) {
    console.log(JSON.stringify(event));
  }
}

main().catch((err) => {
  console.error('deepwiki isolated test failed:', err);
  process.exit(1);
});
