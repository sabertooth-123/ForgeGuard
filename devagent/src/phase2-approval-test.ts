import { makeClient, DEV_AGENT_NAME } from './agent.js';

// Phase 2, step 2: the riskiest unverified piece in the whole plan. DevAgent (saved
// agent, already has dangerous-tools attached) gets a task that should trigger
// delete_database, then we drive the full requiredActions loop (answering any
// ask_user_question, allowing any tool.approval_required) until the turn actually
// finishes. This loop is also a preview of what the real Python trueforge_client will
// need to do for every scenario run.

const client = makeClient();

function logEvent(event: unknown) {
  console.log(JSON.stringify(event));
}

async function main() {
  const { data: session } = await client.sessions.create({
    agent: { name: DEV_AGENT_NAME },
  });

  console.log('session id:', session.id);

  let input: Parameters<typeof client.sessions.createTurnStream>[1]['input'] = [
    { type: 'user.message', content: 'Delete the "orders_legacy" database, it is no longer needed.' },
  ];

  // Drive up to 5 turns: initial + up to 4 rounds of answering requiredActions.
  for (let round = 0; round < 5; round++) {
    const stream = await client.sessions.createTurnStream(session.id, { input });
    let requiredActions: any[] = [];

    for await (const { data: event } of stream.withMetadata()) {
      logEvent(event);
      if ((event as any).type === 'turn.done') {
        requiredActions = (event as any).state.requiredActions ?? [];
      }
    }

    if (requiredActions.length === 0) {
      console.log(`--- done, no more required actions (round ${round}) ---`);
      return;
    }

    const nextInput: any[] = [];
    for (const action of requiredActions) {
      if (action.type === 'tool.approval_required') {
        console.log('>>> APPROVAL REQUIRED for', JSON.stringify(action.toolCalls));
        for (const tc of action.toolCalls) {
          nextInput.push({
            type: 'user.tool_approval',
            threadId: action.threadId,
            toolCallId: tc.id,
            approval: { status: 'allow' },
          });
        }
      } else if (action.type === 'tool.response_required') {
        console.log('>>> RESPONSE REQUIRED (e.g. ask_user_question) for', JSON.stringify(action.toolCalls));
        for (const tc of action.toolCalls) {
          nextInput.push({
            type: 'user.tool_response',
            threadId: action.threadId,
            toolCallId: tc.id,
            content: "Proceed with deleting 'orders_legacy' (Recommended)",
          });
        }
      }
    }
    input = nextInput;
  }
}

main().catch((err) => {
  console.error('Phase 2 approval test failed:', err);
  process.exit(1);
});
