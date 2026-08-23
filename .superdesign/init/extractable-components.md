# Extractable components

The current UI is a single page and has no independently exported reusable
components. These inline patterns can become components after the redesign is
approved.

## SiteHeader

- Source: `frontend/src/App.tsx`
- Category: layout
- Description: StayLong wordmark with How it works and Urgent help anchors.
- Extractable props: activeItem (string, default: "home")
- Hardcoded: wordmark text and navigation labels

## SiteFooter

- Source: `frontend/src/App.tsx`
- Category: layout
- Description: Product boundary and non-clinical disclaimer.
- Extractable props: none
- Hardcoded: all boundary copy

## ProgressPath

- Source: `frontend/src/App.tsx`
- Category: basic
- Description: Three-step explanation of the current coordination path.
- Extractable props: activeStep (number, default: 1)
- Hardcoded: step labels and descriptions

