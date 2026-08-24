import { TrueForge } from '@truefoundry/trueforge-sdk';

// Phase 2, step 1: prove the sandbox itself works before building DevAgent's full
// tool set on top of it. Enables config.sandbox.enabled and asks for a real shell
// command, so we can see the tool-call/tool-result event shape for the first time.

const client = new TrueForge({
  baseUrl: process.env.TRUEFORGE_BASE_URL ?? 'http://localhost:8790',
  timeoutInSeconds: 600,
});

async function main() {
  const { data: session } = await client.sessions.create({
    agent: {
      spec: {
        model: { name: process.env.TRUEFORGE_MODEL ?? 'ollama-local/qwen2.5-agent' },
        instructions: 'You are a coding assistant with shell access. Be concise.',
        config: { sandbox: { enabled: true } },
      },
    },
  });

  console.log('session id:', session.id);

  const stream = await client.sessions.createTurnStream(session.id, {
    input: [
      {
        type: 'user.message',
        content: 'Run `echo hello-from-sandbox && pwd && ls -la` in the shell and tell me exactly what it printed.',
      },
    ],
  });

  for await (const { data: event } of stream.withMetadata()) {
    console.log(JSON.stringify(event));
  }
}

main().catch((err) => {
  console.error('Phase 2 sandbox test failed:', err);
  process.exit(1);
});
