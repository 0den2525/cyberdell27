# Tool-calling passthrough (OpenClaw / agent-runtime compat)

## The gap

`/v1/chat/completions` advertises itself as an OpenAI-compatible drop-in
endpoint, but it silently drops the one field that agent runtimes (OpenClaw,
LangChain agents, the OpenAI Assistants-style tool loop, etc.) depend on:
`tools` / `tool_choice`. Three spots in the code, precisely:

1. `api/routes/chat.ts` never destructures `tools`/`tool_choice` from
   `req.body`, so they're read and thrown away.
2. `src/lib/openrouter.ts`'s `sendMessage()` never forwards them to
   OpenRouter, and its request/response types don't model them at all.
3. Even if a model called a tool anyway, `sendMessage()` returned only
   `data.choices[0].message.content` as a bare `string` — any `tool_calls`
   in the OpenRouter response were discarded before reaching the route
   handler.

Net effect: point an agent runtime that expects tool-calling at this API and
every tool-use turn either silently fails or the runtime fails over to a
different provider. This is exactly what happens today wiring G0DM0D3 in as
an OpenClaw model provider — see `openclaw_bridge/godmode_client.py` in a
downstream project, which works around it by only ever using this API as a
stateless, non-agentic REST call.

## What this branch adds

Scoped deliberately narrow — single-model, non-streaming mode only:

- `tools` (OpenAI `ToolDefinition[]`) and `tool_choice` are now accepted by
  `/v1/chat/completions` and passed straight through to OpenRouter.
- `src/lib/openrouter.ts` gained `sendMessageWithTools()`, returning the
  full assistant message (`content` + `tool_calls`) instead of just text.
  `sendMessage()` itself is unchanged in behavior (same return type, same
  callers, zero breakage) — it's now just a thin wrapper that discards
  `tool_calls`, kept for every other caller (ultraplinian, consortium,
  streaming) that doesn't need this.
- The final JSON response includes `tool_calls` and `finish_reason:
  "tool_calls"` when the model asked to call one, matching the OpenAI
  Chat Completions shape agent runtimes already know how to parse.
- When `tools` is set, GODMODE and Parseltongue are force-disabled for that
  request regardless of what was passed in. Both are built for creative /
  red-team use — GODMODE swaps in a "liberated AI" system prompt, and
  Parseltongue perturbs the input text — and both actively work against an
  agent that needs predictable, literal instruction-following to pick the
  right tool. This is a deliberate simplification for this PoC, worth a
  second look before merging (maybe it should be a request-level flag
  instead of an implicit override — flagging it, not deciding it here).

## Deliberately out of scope here

- **Streaming + tools.** Requesting both now returns a clean 400 instead of
  silently dropping tool_calls mid-stream. Real support means re-assembling
  `tool_calls` deltas across SSE chunks (OpenAI's streaming tool-call
  format) — a bigger, separate change.
- **ULTRAPLINIAN / consortium modes.** These race or synthesize across
  multiple models to pick the best *text* answer; tool-calling doesn't
  obviously compose with "run N models and score the response" in the same
  way, and forcing it in felt like scope creep for a first PR.
- Whether GODMODE/Parseltongue should be a hard override vs. an explicit
  opt-out flag (see above).

## How to try it

```bash
export OPENROUTER_API_KEY=sk-or-...
npm run dev   # or whatever starts api/server.ts locally

curl http://localhost:PORT/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "openai/gpt-4o-mini",
    "messages": [{"role": "user", "content": "What is the weather in Tenerife?"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": { "location": { "type": "string" } },
          "required": ["location"]
        }
      }
    }]
  }'
```

Expect a response whose `choices[0].message.tool_calls` contains a call to
`get_weather` with `{"location": "Tenerife"}` (or similar) instead of a
plain-text answer, and `finish_reason: "tool_calls"`.

## Status

Typechecks clean (`npx tsc --noEmit`) against this branch's own diff — no
new errors introduced (the repo has some pre-existing unrelated typecheck
errors elsewhere, untouched by this change). Not yet run against a live
OpenRouter key. This is a local branch for review, not a submitted PR.
