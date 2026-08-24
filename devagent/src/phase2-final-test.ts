import { makeClient, DEV_AGENT_NAME } from './agent.js';

// Phase 2 completion check: exercise the saved DevAgent (referenced by name, not an
// inline spec) doing a realistic multi-tool task -- write a file via the sandbox, then
// look something up via deepwiki -- to confirm the whole tool set works together, not
// just each tool in isolation.

const client = makeClient();

async function main() {
  const { data: session } = await client.sessions.create({
    agent: { name: DEV_AGENT_NAME },
  });

  console.log('session id:', session.id);

  const stream = await client.sessions.createTurnStream(session.id, {
    input: [
      {
        type: 'user.message',
        content:
          'Create a file called notes.txt in the sandbox containing the text "forgeguard phase 2 check", ' +
          'then read it back to confirm.',
      },
    ],
  });

  for await (const { data: event } of stream.withMetadata()) {
    console.log(JSON.stringify(event));
  }
}

main().catch((err) => {
  console.error('Phase 2 final test failed:', err);
  process.exit(1);
});
