// @vitest-environment node

import { createServer as createHttpServer } from 'node:http'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import {
  build,
  createServer as createViteServer,
  preview,
  type PreviewServer,
  type ViteDevServer,
} from 'vite'

describe('local StayLong UI API connection', () => {
  let vite: ViteDevServer | undefined
  let vitePreview: PreviewServer | undefined
  let api: ReturnType<typeof createHttpServer> | undefined

  afterEach(async () => {
    await vite?.close()
    await vitePreview?.close()
    await new Promise<void>((resolveClose, reject) => {
      if (!api?.listening) return resolveClose()
      api.close((error) => (error ? reject(error) : resolveClose()))
    })
    delete process.env.STAYLONG_API_PROXY_TARGET
  })

  it('forwards case creation from the local UI origin to the API', async () => {
    api = createHttpServer((request, response) => {
      if (request.method === 'POST' && request.url === '/v1/cases') {
        response.writeHead(201, { 'content-type': 'application/json' })
        response.end(JSON.stringify({ case_id: 'case-local', status: 'open' }))
        return
      }
      response.writeHead(404).end()
    })
    await new Promise<void>((resolveListen) => api?.listen(0, '127.0.0.1', resolveListen))
    const apiAddress = api.address()
    if (!apiAddress || typeof apiAddress === 'string') throw new Error('API test server did not start')
    process.env.STAYLONG_API_PROXY_TARGET = `http://127.0.0.1:${apiAddress.port}`

    vite = await createViteServer({
      root: resolve(import.meta.dirname),
      configFile: resolve(import.meta.dirname, 'vite.config.ts'),
      server: { host: '127.0.0.1', port: 0 },
      logLevel: 'silent',
    })
    await vite.listen()
    const viteAddress = vite.httpServer?.address()
    if (!viteAddress || typeof viteAddress === 'string') throw new Error('Vite test server did not start')

    const response = await fetch(`http://127.0.0.1:${viteAddress.port}/v1/cases`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer demo-token',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ summary: 'Getting to the bathroom at night is difficult.' }),
    })

    expect(response.status).toBe(201)
    expect(await response.json()).toEqual({ case_id: 'case-local', status: 'open' })
  })

  it('forwards case creation from the production preview origin to the API', async () => {
    api = createHttpServer((request, response) => {
      if (request.method === 'POST' && request.url === '/v1/cases') {
        response.writeHead(201, { 'content-type': 'application/json' })
        response.end(JSON.stringify({ case_id: 'case-preview', status: 'open' }))
        return
      }
      response.writeHead(404).end()
    })
    await new Promise<void>((resolveListen) => api?.listen(0, '127.0.0.1', resolveListen))
    const apiAddress = api.address()
    if (!apiAddress || typeof apiAddress === 'string') throw new Error('API test server did not start')
    process.env.STAYLONG_API_PROXY_TARGET = `http://127.0.0.1:${apiAddress.port}`

    const root = resolve(import.meta.dirname)
    const configFile = resolve(root, 'vite.config.ts')
    await build({ root, configFile, logLevel: 'silent' })
    vitePreview = await preview({
      root,
      configFile,
      preview: { host: '127.0.0.1', port: 0 },
      logLevel: 'silent',
    })
    const previewAddress = vitePreview.httpServer.address()
    if (!previewAddress || typeof previewAddress === 'string') {
      throw new Error('Vite preview test server did not start')
    }

    const response = await fetch(`http://127.0.0.1:${previewAddress.port}/v1/cases`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer demo-token',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ summary: 'Getting to the bathroom at night is difficult.' }),
    })

    expect(response.status).toBe(201)
    expect(await response.json()).toEqual({ case_id: 'case-preview', status: 'open' })
  })
})
