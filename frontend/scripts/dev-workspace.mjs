import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const frontendDirectory = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(frontendDirectory, '..')
const repositoryRoot = resolve(frontendRoot, '..')
const apiPort = process.env.STAYLONG_LOCAL_API_PORT ?? '8000'
const apiTarget = `http://127.0.0.1:${apiPort}`
const apiToken = process.env.STAYLONG_API_TOKEN ?? 'demo-token'
const viteCli = resolve(frontendRoot, 'node_modules/vite/bin/vite.js')
let api
let vite

function stop(child) {
  if (child && !child.killed) child.kill('SIGTERM')
}

function exitWithError(message) {
  console.error(`StayLong local workspace: ${message}`)
  stop(api)
  stop(vite)
  process.exitCode = 1
}

async function waitForApi() {
  const deadline = Date.now() + 10_000
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${apiTarget}/health`)
      if (response.ok) return
    } catch {
      // The API is still starting; keep the browser unavailable until it is ready.
    }
    await new Promise((resolveDelay) => setTimeout(resolveDelay, 100))
  }
  throw new Error(`API did not become healthy at ${apiTarget}/health`)
}

async function start() {
  api = spawn(
    'uv',
    [
      'run',
      '--project',
      repositoryRoot,
      'uvicorn',
      'staylong.api.main:app',
      '--app-dir',
      resolve(repositoryRoot, 'src'),
      '--host',
      '127.0.0.1',
      '--port',
      apiPort,
    ],
    {
      cwd: repositoryRoot,
      env: { ...process.env, STAYLONG_API_TOKEN: apiToken, STAYLONG_LOCAL_DEMO: 'true' },
      stdio: 'inherit',
    },
  )

  api.once('error', (error) => exitWithError(`could not start the API: ${error.message}`))
  api.once('exit', (code) => {
    if (!vite && code !== 0) exitWithError(`API stopped before startup (exit ${code ?? 'signal'})`)
  })

  await waitForApi()

  vite = spawn(process.execPath, [viteCli, ...process.argv.slice(2)], {
    cwd: frontendRoot,
    env: {
      ...process.env,
      STAYLONG_API_PROXY_TARGET: apiTarget,
      STAYLONG_API_PROXY_TOKEN: apiToken,
    },
    stdio: 'inherit',
  })
  vite.once('error', (error) => exitWithError(`could not start the UI: ${error.message}`))
  vite.once('exit', (code) => {
    stop(api)
    process.exitCode = code ?? 1
  })
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, () => {
    stop(api)
    stop(vite)
    process.exit(0)
  })
}

start().catch((error) => exitWithError(error instanceof Error ? error.message : String(error)))
