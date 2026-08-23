# Routes

StayLong is a Vite React single-page application with no client-side router.

| URL | Entry | Layout |
| --- | --- | --- |
| `/` | `frontend/src/App.tsx` | Inline application shell |
| `/#how-it-works` | In-page anchor | Inline application shell |
| `/#urgent-help` | In-page anchor | Inline application shell |

## Application entry

`frontend/src/main.tsx`

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

