import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveProviderCredentials } from '../api/lib/llm-provider'
import { classifyModelError, getModelsForTier, queryModel } from '../api/lib/ultraplinian'
import {
  getLlmProviderEndpoint,
  getLlmProviderHeaders,
} from '../src/lib/llm-provider'
import { sendMessage, sendMessageViaProxy, streamMessage } from '../src/lib/openrouter'

test('builds Atlas Cloud endpoint and headers without OpenRouter metadata', () => {
  assert.equal(
    getLlmProviderEndpoint('atlascloud'),
    'https://api.atlascloud.ai/v1/chat/completions',
  )
  assert.deepEqual(getLlmProviderHeaders('atlascloud', 'atlas-key'), {
    Authorization: 'Bearer atlas-key',
    'Content-Type': 'application/json',
  })
})

test('resolves Atlas Cloud credentials from request and environment', () => {
  assert.deepEqual(
    resolveProviderCredentials({
      provider: 'atlascloud',
      atlasCloudApiKey: 'request-key',
      env: { ATLASCLOUD_API_KEY: 'env-key' },
    }),
    { provider: 'atlascloud', apiKey: 'request-key' },
  )

  assert.deepEqual(
    resolveProviderCredentials({
      provider: 'atlascloud',
      env: { ATLASCLOUD_API_KEY: 'env-key' },
    }),
    { provider: 'atlascloud', apiKey: 'env-key' },
  )
})

test('rejects invalid providers and missing credentials', () => {
  assert.throws(
    () => resolveProviderCredentials({ provider: 'other', env: {} }),
    /llm_provider must be either/,
  )
  assert.throws(
    () => resolveProviderCredentials({ provider: 'atlascloud', env: {} }),
    /No Atlas Cloud API key available/,
  )
})

test('uses Atlas Cloud model tiers for races', () => {
  const models = getModelsForTier('fast', 'atlascloud')
  assert.ok(models.includes('google/gemini-2.5-flash'))
  assert.ok(models.includes('deepseek-ai/deepseek-v3.2'))
  assert.ok(!models.includes('deepseek/deepseek-chat'))
})

test('routes race-model queries through Atlas Cloud', async () => {
  const originalFetch = globalThis.fetch
  let capturedUrl = ''
  let capturedInit: RequestInit | undefined

  globalThis.fetch = async (input, init) => {
    capturedUrl = String(input)
    capturedInit = init
    return new Response(JSON.stringify({
      choices: [{ message: { content: 'race response' } }],
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const result = await queryModel(
      'google/gemini-2.5-flash',
      [{ role: 'user', content: 'hello' }],
      'atlas-key',
      {},
      undefined,
      'atlascloud',
    )

    assert.equal(result.success, true)
    assert.equal(result.content, 'race response')
    assert.equal(capturedUrl, 'https://api.atlascloud.ai/v1/chat/completions')
    assert.deepEqual(capturedInit?.headers, {
      Authorization: 'Bearer atlas-key',
      'Content-Type': 'application/json',
    })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('sends direct chat requests to Atlas Cloud', async () => {
  const originalFetch = globalThis.fetch
  let capturedUrl = ''
  let capturedInit: RequestInit | undefined

  globalThis.fetch = async (input, init) => {
    capturedUrl = String(input)
    capturedInit = init
    return new Response(JSON.stringify({
      choices: [{ message: { content: 'atlas response' } }],
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const result = await sendMessage({
      messages: [{ role: 'user', content: 'hello' }],
      model: 'google/gemini-2.5-flash',
      apiKey: 'atlas-key',
      provider: 'atlascloud',
      noLog: true,
    })

    assert.equal(result, 'atlas response')
    assert.equal(capturedUrl, 'https://api.atlascloud.ai/v1/chat/completions')
    assert.deepEqual(capturedInit?.headers, {
      Authorization: 'Bearer atlas-key',
      'Content-Type': 'application/json',
    })

    const body = JSON.parse(String(capturedInit?.body))
    assert.equal(body.model, 'google/gemini-2.5-flash')
    assert.equal(body.provider, undefined)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('selects Atlas Cloud for server-side proxy requests', async () => {
  const originalFetch = globalThis.fetch
  let capturedInit: RequestInit | undefined

  globalThis.fetch = async (_input, init) => {
    capturedInit = init
    return new Response(JSON.stringify({
      choices: [{ message: { content: 'proxy response' } }],
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const result = await sendMessageViaProxy({
      messages: [{ role: 'user', content: 'hello' }],
      model: 'google/gemini-2.5-flash',
      provider: 'atlascloud',
      apiBaseUrl: 'https://example.test',
      godmodeApiKey: 'godmode-key',
    })

    assert.equal(result, 'proxy response')
    const body = JSON.parse(String(capturedInit?.body))
    assert.equal(body.llm_provider, 'atlascloud')
  } finally {
    globalThis.fetch = originalFetch
  }
})

// ── Failure-boundary and contract tests ─────────────────────────────

const ATLAS_URL = 'https://api.atlascloud.ai/v1/chat/completions'
const msgs = [{ role: 'user' as const, content: 'hello' }]

function mockFetch(handler: (url: string, init?: RequestInit) => Promise<Response> | Response) {
  const original = globalThis.fetch
  const urls: string[] = []
  globalThis.fetch = (async (input: any, init?: RequestInit) => {
    urls.push(String(input))
    return handler(String(input), init)
  }) as typeof fetch
  return { urls, restore: () => { globalThis.fetch = original } }
}

const json = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })

test('sendMessage maps Atlas Cloud 401 to an Atlas-specific message and never falls back', async () => {
  const m = mockFetch(() => json(401, { error: { message: 'Invalid API key' } }))
  try {
    await assert.rejects(
      sendMessage({ messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'bad', provider: 'atlascloud' }),
      /Atlas Cloud API key is invalid/,
    )
    assert.deepEqual(m.urls, [ATLAS_URL])
  } finally { m.restore() }
})

test('sendMessage maps Atlas Cloud 429 to a rate-limit message and does not retry elsewhere', async () => {
  const m = mockFetch(() => json(429, { error: { message: 'slow down' } }))
  try {
    await assert.rejects(
      sendMessage({ messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'k', provider: 'atlascloud' }),
      /Rate limited by Atlas Cloud/,
    )
    assert.deepEqual(m.urls, [ATLAS_URL])
  } finally { m.restore() }
})

test('sendMessage rejects a 200 response without choices', async () => {
  const m = mockFetch(() => json(200, { id: 'x' }))
  try {
    await assert.rejects(
      sendMessage({ messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'k', provider: 'atlascloud' }),
      /No response from model/,
    )
  } finally { m.restore() }
})

test('sendMessage surfaces a non-JSON 200 body as an error', async () => {
  const m = mockFetch(() => new Response('<html>oops</html>', { status: 200 }))
  try {
    await assert.rejects(
      sendMessage({ messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'k', provider: 'atlascloud' }),
    )
  } finally { m.restore() }
})

test('sendMessage propagates caller abort (timeout) without contacting another provider', async () => {
  const controller = new AbortController()
  const m = mockFetch((_url, init) => new Promise((_resolve, reject) => {
    init?.signal?.addEventListener('abort', () => {
      const e = new Error('aborted'); e.name = 'AbortError'; reject(e)
    })
  }))
  try {
    const p = sendMessage({
      messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'k',
      provider: 'atlascloud', signal: controller.signal,
    })
    setTimeout(() => controller.abort(), 10)
    await assert.rejects(p, (e: any) => e.name === 'AbortError')
    assert.deepEqual(m.urls, [ATLAS_URL])
  } finally { m.restore() }
})

test('streamMessage streams Atlas Cloud SSE deltas and sets stream:true', async () => {
  let body: any
  const sse = [
    'data: {"choices":[{"delta":{"content":"Hel"}}]}',
    'data: not-json',
    'data: {"choices":[{"delta":{"content":"lo"}}]}',
    'data: [DONE]',
    '',
  ].join('\n')
  const m = mockFetch((_url, init) => {
    body = JSON.parse(String(init?.body))
    return new Response(sse, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
  })
  try {
    let out = ''
    for await (const chunk of streamMessage({
      messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'k', provider: 'atlascloud',
    })) out += chunk
    assert.equal(out, 'Hello')
    assert.equal(body.stream, true)
    assert.deepEqual(m.urls, [ATLAS_URL])
  } finally { m.restore() }
})

test('streamMessage reports Atlas Cloud 401 before streaming', async () => {
  const m = mockFetch(() => json(401, { error: { message: 'Unauthorized' } }))
  try {
    await assert.rejects(
      (async () => {
        for await (const _ of streamMessage({
          messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'bad', provider: 'atlascloud',
        })) { /* drain */ }
      })(),
      /Atlas Cloud API key is invalid/,
    )
  } finally { m.restore() }
})

test('queryModel reports 401 from Atlas Cloud as an auth failure', async () => {
  const m = mockFetch(() => json(401, { error: { message: 'Invalid API key' } }))
  try {
    const r = await queryModel('google/gemini-2.5-flash', msgs, 'bad', {}, undefined, 'atlascloud')
    assert.equal(r.success, false)
    assert.equal(classifyModelError(r.error), 'auth')
    assert.deepEqual(m.urls, [ATLAS_URL])
  } finally { m.restore() }
})

test('queryModel retries 429 against Atlas Cloud only, then succeeds', async () => {
  let calls = 0
  const m = mockFetch(() => {
    calls++
    return calls === 1
      ? json(429, { error: { message: 'rate limit' } }, { 'retry-after': '0' })
      : json(200, { choices: [{ message: { content: 'ok' } }] })
  })
  try {
    const r = await queryModel('google/gemini-2.5-flash', msgs, 'k', {}, undefined, 'atlascloud')
    assert.equal(r.success, true)
    assert.equal(calls, 2)
    assert.deepEqual(m.urls, [ATLAS_URL, ATLAS_URL])
  } finally { m.restore() }
})

test('queryModel gives up on persistent 429 and classifies it as rate_limit', async () => {
  const m = mockFetch(() => json(429, { error: { message: 'rate limit' } }, { 'retry-after': '0' }))
  try {
    const r = await queryModel('google/gemini-2.5-flash', msgs, 'k', {}, undefined, 'atlascloud')
    assert.equal(r.success, false)
    assert.equal(classifyModelError(r.error), 'rate_limit')
    assert.ok(m.urls.every(u => u === ATLAS_URL))
  } finally { m.restore() }
})

test('queryModel times out via caller abort and reports timeout', async () => {
  const controller = new AbortController()
  const m = mockFetch((_url, init) => new Promise((_resolve, reject) => {
    init?.signal?.addEventListener('abort', () => {
      const e = new Error('aborted'); e.name = 'AbortError'; reject(e)
    })
  }))
  try {
    const p = queryModel('google/gemini-2.5-flash', msgs, 'k', {}, controller.signal, 'atlascloud')
    setTimeout(() => controller.abort(), 10)
    const r = await p
    assert.equal(r.success, false)
    assert.equal(classifyModelError(r.error), 'timeout')
    assert.deepEqual(m.urls, [ATLAS_URL])
  } finally { m.restore() }
})

test('queryModel treats malformed Atlas Cloud responses as failures', async () => {
  for (const make of [
    () => json(200, { choices: [] }),
    () => json(200, { choices: [{ message: { content: '' } }] }),
    () => new Response('not json', { status: 200 }),
  ]) {
    const m = mockFetch(make)
    try {
      const r = await queryModel('google/gemini-2.5-flash', msgs, 'k', {}, undefined, 'atlascloud')
      assert.equal(r.success, false)
      assert.deepEqual(m.urls, [ATLAS_URL])
    } finally { m.restore() }
  }
})

test('OpenRouter-only options never leak into Atlas Cloud requests', async () => {
  let init: RequestInit | undefined
  const m = mockFetch((_url, i) => { init = i; return json(200, { choices: [{ message: { content: 'x' } }] }) })
  try {
    await sendMessage({
      messages: msgs, model: 'google/gemini-2.5-flash', apiKey: 'k', provider: 'atlascloud', noLog: true,
    })
    const headers = init?.headers as Record<string, string>
    assert.equal(headers['HTTP-Referer'], undefined)
    assert.equal(headers['X-Title'], undefined)
    assert.equal(JSON.parse(String(init?.body)).provider, undefined)
    assert.equal(m.urls.some(u => u.includes('openrouter.ai')), false)
  } finally { m.restore() }
})

test('provider defaults to OpenRouter and Atlas Cloud is never implied', () => {
  assert.equal(resolveProviderCredentials({ openRouterApiKey: 'or', env: {} }).provider, 'openrouter')
  assert.throws(
    () => resolveProviderCredentials({ openRouterApiKey: 'or', provider: 'atlascloud', env: {} }),
    /No Atlas Cloud API key available/,
  )
  assert.ok(!getModelsForTier('fast', 'openrouter').includes('deepseek-ai/deepseek-v3.2'))
})
