# Page dependency trees

## `/` — StayLong home and plan entry

Entry: `frontend/src/App.tsx`

Dependencies:

- `frontend/src/App.tsx`
  - `frontend/src/App.css`
- `frontend/src/main.tsx`
  - `frontend/src/index.css`
  - `frontend/src/App.tsx`
- `frontend/index.html`

The page has four visual states in one component: introductory home, concern
composer, loading/error status, and recorded-concern confirmation.

