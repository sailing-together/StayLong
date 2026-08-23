// @vitest-environment node

import { createServer } from 'node:net'
import { spawn, type ChildProcess } from 'node:child_process'
import { afterEach, describe, expect, it } from 'vitest'

async function reservePort(): Promise<number> {
  const server = createServer()
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('Could not reserve a local port')
  await new Promise<void>((resolve, reject) => server.close((error) => (error ? reject(error) : resolve())))
  return address.port
}

async function waitFor(url: string): Promise<Response> {
  const deadline = Date.now() + 15_000
  let lastError: unknown
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url)
      if (response.ok) return response
    } catch (error) {
      lastError = error
    }
    await new Promise((resolve) => setTimeout(resolve, 150))
  }
  throw new Error(`Timed out waiting for ${url}: ${String(lastError)}`)
}

describe('npm run dev', () => {
  let workspace: ChildProcess | undefined

  afterEach(() => {
    workspace?.kill('SIGTERM')
  })

  it('starts the local API before the UI forwards an authenticated plan request', async () => {
    const apiPort = await reservePort()
    const uiPort = await reservePort()
    workspace = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(uiPort), '--strictPort'], {
      cwd: import.meta.dirname,
      env: {
        ...process.env,
        STAYLONG_API_TOKEN: 'demo-token',
        STAYLONG_LOCAL_API_PORT: String(apiPort),
      },
      stdio: 'ignore',
    })

    await waitFor(`http://127.0.0.1:${uiPort}/`)
    const response = await fetch(`http://127.0.0.1:${uiPort}/v1/cases`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ summary: 'Getting to the bathroom at night is difficult.' }),
    })

    expect(response.status).toBe(201)
    expect(await response.json()).toMatchObject({ case_id: expect.stringMatching(/^case-/), status: 'open' })
  }, 20_000)
})
