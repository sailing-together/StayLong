# Shared layouts

There is one self-contained application shell in `frontend/src/App.tsx`. It
renders the StayLong wordmark, compact top navigation, the current page state,
urgent-help content, and the footer. There is no separate layout component or
router-level shell.

The rendered hierarchy is:

```text
App
├── skip link
├── site header
├── main
│   ├── hero
│   ├── conditional concern composer
│   ├── status message
│   ├── conditional recorded concern
│   ├── how-it-works steps
│   └── urgent-help notice
└── footer
```

Full shell and page source: `frontend/src/App.tsx`.

