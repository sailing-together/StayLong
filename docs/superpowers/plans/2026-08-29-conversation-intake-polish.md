# Conversation-Style StayLong Intake Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make StayLong’s first step feel like a calm, optional conversation while preserving the existing workflow and allowing free-form concerns.

**Architecture:** Keep the current concern state and API payload unchanged. Add presentational conversation cues around the existing example buttons and textarea, move the emergency instruction from the top bar into the footer, and preserve the example-free path.

**Tech Stack:** React, TypeScript, CSS, Vitest, Testing Library.

**Spec:** Product-design audit of StayLong against AskSafe Home’s guided intake pattern.

## Global Constraints

- Do not modify `/Users/yvonne/Documents/projects/asksafe-home`.
- Do not add a mandatory category-selection step.
- Examples remain optional; free-form text must remain a first-class path.
- Do not add voice capture in this pass.

### Task 1: Intake copy and emergency notice

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`
- Modify: `frontend/src/App.css`

- [ ] Add failing tests for the conversational prompt, optional-example copy, free-form helper, and footer emergency notice with no top emergency bar.
- [ ] Run the focused test and confirm it fails for the missing labels.
- [ ] Implement the copy/layout changes without changing the workflow request body.
- [ ] Run focused tests, then the full frontend test, lint, and build.
- [ ] Inspect the rendered first step at desktop and mobile widths.
- [ ] Commit as `feat: refine staylong conversational intake`.

### Task 2: Verification handoff

- [ ] Confirm AskSafe Home has no modified files.
- [ ] Confirm the free-form concern path still enables `Start my plan` and sends the same `concern` payload.
- [ ] Record the changed files and verification results for review.
