# StayLong family workspace

The StayLong family workspace is a React and TypeScript interface served by the
StayLong API container. It lets an authorised family member create a real
case-flow concern and see the API-returned case path.

## Local development

```sh
npm ci
npm run dev
```

Use `VITE_API_BASE_URL` only when the API is hosted separately. The access
token is intentionally held in React state and is never written to browser
storage.

## Quality checks

```sh
npm run lint
npm test
npm run build
```

The root Dockerfile builds this workspace and copies the production bundle into
the FastAPI image.
