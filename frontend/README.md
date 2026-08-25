# StayLong Calm Companion

The StayLong independent-living workspace is a React and TypeScript interface
served by the StayLong API container. Its Calm Companion experience lets an
older person living alone describe a real home concern, see the API-returned
case path, and retain approval over sharing and follow-up. Trusted supporters
are optional and require the person's choice.

The normal first screen contains one primary action and no credential field.
The local development proxy holds the sandbox API token on the server side, so
it is never exposed to, requested from, or written by the browser.

## Local development

From `frontend/`, start the complete local workspace:

```sh
npm ci
npm run dev
```

This starts the local API, waits for its health check, then starts the React
workspace. Open the local URL and start a plan. `STAYLONG_API_TOKEN` may override the local token;
`STAYLONG_LOCAL_API_PORT` may override port `8000`. Use `npm run dev:ui` only
when a separate API is already running; set `STAYLONG_API_PROXY_TARGET` to that
API's origin. Use `VITE_API_BASE_URL` only when the API is hosted separately
and supports browser cross-origin requests.

The development token is held only by the local proxy and is never written to
browser storage or displayed in the user interface.

## Quality checks

```sh
npm run lint
npm test
npm run build
```

The root Dockerfile builds this workspace and copies the production bundle into
the FastAPI image.
