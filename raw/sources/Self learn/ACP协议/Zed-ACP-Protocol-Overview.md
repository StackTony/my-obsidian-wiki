---
credibility: low
---

The Agent Client Protocol allows [Agents](#agent) and [Clients](#client) to communicate by exposing methods that each side can call and sending notifications to inform each other of events.

## Communication Model

The protocol follows the [JSON-RPC 2.0](https://www.jsonrpc.org/specification) specification with two types of messages:

- Methods are request-response pairs that expect a result or error.
- Notifications are one-way messages that don’t expect a response.

## Message flow

A typical flow follows this pattern:

## Agent

Agents are programs that use generative AI to autonomously modify code. They typically run as subprocesses of the Client.

### Baseline methodsAuthenticate with the Agent (if required).[Send user prompts](https://agentclientprotocol.com/protocol/v1/prompt-turn#1-user-message) to the Agent.

### Optional methods[Load an existing session](https://agentclientprotocol.com/protocol/v1/session-setup#loading-sessions) (requires `loadSession` capability).[End the current authenticated state](https://agentclientprotocol.com/protocol/v1/authentication#logging-out) (requires `agentCapabilities.auth.logout` capability).

### Notifications[Cancel ongoing operations](https://agentclientprotocol.com/protocol/v1/prompt-turn#cancellation) (no response expected).

## Client

Clients provide the interface between users and agents. They are typically code editors (IDEs, text editors) but can also be other UIs for interacting with agents. Clients manage the environment, handle user interactions, and control access to resources.

### Baseline methods[Request user authorization](https://agentclientprotocol.com/protocol/v1/tool-calls#requesting-permission) for tool calls.

### Optional methods[Read file contents](https://agentclientprotocol.com/protocol/v1/file-system#reading-files) (requires `fs.readTextFile` capability).[Write file contents](https://agentclientprotocol.com/protocol/v1/file-system#writing-files) (requires `fs.writeTextFile` capability).[Create a new terminal](https://agentclientprotocol.com/protocol/v1/terminals) (requires `terminal` capability).Get terminal output and exit status (requires `terminal` capability).Release a terminal (requires `terminal` capability).Wait for terminal command to exit (requires `terminal` capability).Kill terminal command without releasing (requires `terminal` capability).[Request structured information from the user](https://agentclientprotocol.com/protocol/v1/elicitation) (requires the matching `elicitation` mode capability).

### Notifications[Report completion of an out-of-band URL interaction](https://agentclientprotocol.com/protocol/v1/elicitation#url-completion) (no response expected).[Send session updates](https://agentclientprotocol.com/protocol/v1/prompt-turn#3-agent-reports-output) to inform the Client of changes (no response expected). This includes:

- [Message chunks](https://agentclientprotocol.com/protocol/v1/content) (agent, user, thought)
- [Tool calls and updates](https://agentclientprotocol.com/protocol/v1/tool-calls)
- [Plans](https://agentclientprotocol.com/protocol/v1/agent-plan)
- [Available commands updates](https://agentclientprotocol.com/protocol/v1/slash-commands#advertising-commands)
- [Mode changes](https://agentclientprotocol.com/protocol/v1/session-modes#from-the-agent)
- [User-facing notices](https://agentclientprotocol.com/protocol/v1/prompt-turn#session-notices)
- [Context compactions](https://agentclientprotocol.com/protocol/v1/prompt-turn#session-compaction)

## Argument requirements

- All file paths in the protocol **MUST** be absolute.
- Line numbers are 1-based

## Error handling

All methods follow standard JSON-RPC 2.0 [error handling](https://www.jsonrpc.org/specification#error_object):

- Successful responses include a `result` field
- Errors include an `error` object with `code` and `message`
- Notifications never receive responses (success or error)

See [Errors](https://agentclientprotocol.com/protocol/v1/error) for the error codes ACP uses and when to use them.

## Conventions

Unless explicitly defined otherwise in the schema, ACP-defined JSON object property keys use `camelCase`. String values carried by discriminator fields use `snake_case`. The JSON-RPC envelope fields (`jsonrpc`, `id`, `method`, `params`, `result`, and `error`) follow the JSON-RPC 2.0 specification.

## Extensibility

Implementations can extend the protocol without breaking compatibility:

- Add custom data using `_meta` fields
- Create custom methods by prefixing their name with underscore (`_`)
- Advertise custom capabilities during initialization

See [Extensibility](https://agentclientprotocol.com/protocol/v1/extensibility) for details.

## Next steps

- [Security Considerations](https://agentclientprotocol.com/protocol/v1/security) covers the trust model. Read it before shipping an Agent or Client.
- [Initialization](https://agentclientprotocol.com/protocol/v1/initialization) covers version and capability negotiation.
- [Session Setup](https://agentclientprotocol.com/protocol/v1/session-setup) covers creating and loading sessions.
- [Prompt Turn](https://agentclientprotocol.com/protocol/v1/prompt-turn) covers the prompt turn lifecycle.
- [Extensibility](https://agentclientprotocol.com/protocol/v1/extensibility) covers custom data, methods, and capabilities.
- The [Test Compatibility Kit](https://agentclientprotocol.com/libraries/testing) checks an Agent implementation against the protocol.