import { TrueForge } from '@truefoundry/trueforge-sdk';

// Phase 1 goal (see ForgeGuard plan): prove task -> TrueForge -> agent -> result works
// end to end against a local `npx @truefoundry/trueforge` server, and print the raw
// event stream so we can see the real event shape instead of guessing at it.
// No tools/sandbox yet -- that's Phase 2, once a sandbox provider is configured.

const client = new TrueForge({
  baseUrl: process.env.TRUEFORGE_BASE_URL ?? 'http://localhost:8790',
  timeoutInSeconds: 600,
});

async function main() {
  const { data: session } = await client.sessions.create({
    agent: {
      spec: {
        model: { name: process.env.TRUEFORGE_MODEL ?? 'ollama-local/qwen2.5-agent' },
        instructions: 'You are a concise, helpful assistant.',
      },
    },
  });

  console.log('session id:', session.id);

  const stream = await client.sessions.createTurnStream(session.id, {
    input: [{ type: 'user.message', content: 'In two sentences, what is TrueForge?' }],
  });

  for await (const { data: event } of stream.withMetadata()) {
    console.log(JSON.stringify(event));
  }
}

main().catch((err) => {
  console.error('Phase 1 smoke test failed:', err);
  process.exit(1);
});
