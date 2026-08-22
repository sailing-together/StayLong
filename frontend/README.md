# StayLong Calm Companion

The StayLong independent-living workspace is a React and TypeScript interface
served by the StayLong API container. Its Calm Companion experience lets an
older person living alone describe a real home concern, see the API-returned
case path, and retain approval over sharing and follow-up. Trusted supporters
are optional and require the person's choice.

The normal first screen contains one primary action and no credential field.
For sandbox demonstrations, the API token is available only after opening the
secondary Demo settings panel. It stays in React state and is never written to
browser storage.

## Local development

Start the API in one terminal:

```sh
STAYLONG_API_TOKEN=demo-token uv run uvicorn staylong.api.main:app \
  --app-dir src --host 127.0.0.1 --port 8000
```

Then start the React workspace from `frontend/`:

```sh
npm ci
npm run dev
```

Open the local URL, enter `demo-token` under **Demo settings**, and start a
plan. Both `npm run dev` and `npm run preview` forward `/v1` requests to
`http://127.0.0.1:8000` by default. Set `STAYLONG_API_PROXY_TARGET` when the
local API uses a different origin. Use `VITE_API_BASE_URL` only when the API is
hosted separately and supports browser cross-origin requests.

The access token is intentionally held in React state and is never written to
browser storage.

## Quality checks

```sh
npm run lint
npm test
npm run build
```

The root Dockerfile builds this workspace and copies the production bundle into
the FastAPI image.
