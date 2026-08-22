import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type CaseRecord = { case_id: string; status: string }
type Concern = { concern_id: string; case_id: string; summary: string }
type RequestState = 'idle' | 'saving' | 'success' | 'error'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

function App() {
  const [composerOpen, setComposerOpen] = useState(false)
  const [demoSettingsOpen, setDemoSettingsOpen] = useState(false)
  const [accessToken, setAccessToken] = useState('')
  const [concernSummary, setConcernSummary] = useState('')
  const [caseRecord, setCaseRecord] = useState<CaseRecord | null>(null)
  const [concerns, setConcerns] = useState<Concern[]>([])
  const [requestState, setRequestState] = useState<RequestState>('idle')
  const [message, setMessage] = useState('')
  const concernInput = useRef<HTMLTextAreaElement>(null)
  const recordedConcernSection = useRef<HTMLElement>(null)

  useEffect(() => {
    document.title = 'StayLong | Independent living, coordinated'
  }, [])

  useEffect(() => {
    if (composerOpen) {
      concernInput.current?.focus()
      concernInput.current?.closest('#workspace')?.scrollIntoView?.({
        behavior: 'smooth',
        block: 'start',
      })
    }
  }, [composerOpen])

  const recordedConcern = concerns[0]?.summary
  const hasCase = Boolean(caseRecord && recordedConcern)

  useEffect(() => {
    if (hasCase) recordedConcernSection.current?.focus()
  }, [hasCase])

  function openComposer() {
    setComposerOpen(true)
  }

  function reviewRecordedConcern() {
    recordedConcernSection.current?.focus()
    recordedConcernSection.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  }

  function startCorrection() {
    setConcernSummary(recordedConcern ?? concernSummary)
    setCaseRecord(null)
    setConcerns([])
    setRequestState('idle')
    setMessage('')
    setComposerOpen(true)
  }

  async function createCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setRequestState('saving')
    setMessage('')

    try {
      const response = await fetch(`${apiBaseUrl}/v1/cases`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ summary: concernSummary }),
      })
      if (!response.ok) {
        throw new Error('StayLong could not start your plan. Please check the demo connection and try again.')
      }

      const createdCase = (await response.json()) as CaseRecord
      const concernsResponse = await fetch(
        `${apiBaseUrl}/v1/cases/${createdCase.case_id}/concerns`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (!concernsResponse.ok) {
        throw new Error('Your plan was started, but StayLong could not load the concern yet.')
      }

      setCaseRecord(createdCase)
      setConcerns((await concernsResponse.json()) as Concern[])
      setComposerOpen(false)
      setRequestState('success')
      setMessage('Your concern is recorded. Nothing has been shared or booked.')
    } catch (error) {
      setRequestState('error')
      setMessage(error instanceof Error ? error.message : 'Something went wrong.')
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header">
        <a className="wordmark" href="#main-content" aria-label="StayLong home">
          StayLong
        </a>
        <nav aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#urgent-help">Urgent help</a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero" aria-labelledby="page-title">
          <div className="hero-copy">
            <p className="context-line">Support for living independently at home</p>
            <h1 id="page-title">What would make home easier today?</h1>
            <p className="hero-intro">
              Tell StayLong what is becoming difficult. We will organise the next
              steps, keep track of follow-up, and ask before anything is shared.
            </p>
            {!composerOpen && !hasCase && (
              <button className="primary-action" type="button" onClick={openComposer}>
                Tell StayLong
              </button>
            )}
            {hasCase && (
              <button
                className="primary-action"
                type="button"
                onClick={reviewRecordedConcern}
              >
                Review what StayLong understood
              </button>
            )}
            <p className="control-promise">You decide who can help and what happens next.</p>
          </div>

          <aside className="next-step" aria-labelledby="next-step-title">
            <p className="section-label">Your next step</p>
            <h2 id="next-step-title">
              {hasCase ? 'Check that we understood you correctly.' : 'Start in your own words.'}
            </h2>
            <p>
              {hasCase
                ? 'Your concern is saved. Review it before StayLong prepares any follow-up.'
                : 'There is no form to get right. Describe what you have noticed and why it matters to you.'}
            </p>
            <div className="privacy-line">
              <strong>Private by default</strong>
              <span>Nothing is shared, booked, or paid for without your approval.</span>
            </div>
          </aside>
        </section>

        {composerOpen && !hasCase && (
          <section className="composer-section" id="workspace" aria-labelledby="composer-title">
            <form className="concern-form" onSubmit={createCase}>
              <div className="form-heading">
                <p className="section-label">Tell StayLong</p>
                <h2 id="composer-title">What is getting harder at home?</h2>
                <p>Use plain language. StayLong does not diagnose or provide medical advice.</p>
              </div>

              <label htmlFor="concern-summary">What is getting harder at home?</label>
              <textarea
                ref={concernInput}
                id="concern-summary"
                value={concernSummary}
                onChange={(event) => setConcernSummary(event.target.value)}
                placeholder="For example: getting to the bathroom at night is becoming difficult."
                rows={5}
                maxLength={2000}
                required
              />
              <p className="field-help">Only include information you are comfortable recording.</p>

              <div className="consent-note">
                <strong>You stay in control.</strong>
                <p>Nothing is shared, booked, or paid for without your approval.</p>
              </div>

              <button
                className="demo-settings-toggle"
                type="button"
                onClick={() => setDemoSettingsOpen((current) => !current)}
                aria-expanded={demoSettingsOpen}
                aria-controls="demo-settings"
              >
                Demo settings
              </button>
              {demoSettingsOpen && (
                <div className="demo-settings" id="demo-settings">
                  <label htmlFor="access-token">Demo access token</label>
                  <input
                    id="access-token"
                    type="password"
                    value={accessToken}
                    onChange={(event) => setAccessToken(event.target.value)}
                    autoComplete="off"
                    required
                  />
                  <p className="field-help">Used only for this sandbox session and never saved.</p>
                </div>
              )}

              <button
                className="primary-action form-submit"
                type="submit"
                disabled={requestState === 'saving' || !concernSummary.trim() || !accessToken}
              >
                {requestState === 'saving' ? 'Starting your plan…' : 'Start my plan'}
              </button>
              {!accessToken && (
                <p className="demo-help">This sandbox demo needs a token in Demo settings.</p>
              )}
            </form>
          </section>
        )}

        <p
          className={`global-status ${message ? 'has-message' : ''} ${requestState}`}
          role="status"
          aria-live="polite"
        >
          {message}
        </p>

        {hasCase && (
          <section
            ref={recordedConcernSection}
            className="recorded-concern"
            id="recorded-concern"
            aria-labelledby="recorded-concern-title"
            tabIndex={-1}
          >
            <p className="section-label">Recorded from your words</p>
            <h2 id="recorded-concern-title">StayLong understood this concern</h2>
            <blockquote>{recordedConcern}</blockquote>
            <p className="case-fact">Case status: {caseRecord?.status}</p>
            <p>Nothing has been shared or booked. You can correct this before continuing.</p>
            <button className="secondary-action" type="button" onClick={startCorrection}>
              Start again with a correction
            </button>
          </section>
        )}

        <section className="how-it-works" id="how-it-works" aria-labelledby="path-title">
          <div className="path-intro">
            <p className="section-label">Your independence plan</p>
            <h2 id="path-title">Always know what is happening next.</h2>
            <p>StayLong keeps the work moving, while decisions remain yours.</p>
          </div>
          <ol className="path-list">
            <li>
              <span className="step-number">1</span>
              <div>
                <strong>Tell us what is happening</strong>
                <p>Describe the practical difficulty in your own words.</p>
              </div>
            </li>
            <li>
              <span className="step-number">2</span>
              <div>
                <strong>Prepare for assessment</strong>
                <p>Organise the facts, questions, and official pathway for human review.</p>
              </div>
            </li>
            <li>
              <span className="step-number">3</span>
              <div>
                <strong>Coordinate approved next steps</strong>
                <p>Track agreed appointments, follow-up, and completion.</p>
              </div>
            </li>
          </ol>
        </section>

        <aside className="urgent-help" id="urgent-help" aria-labelledby="urgent-title">
          <div>
            <p className="section-label">Urgent help</p>
            <h2 id="urgent-title">If anyone is in immediate danger, call 000.</h2>
          </div>
          <p>
            StayLong coordinates non-urgent practical support. It is not an emergency,
            medical, or crisis service.
          </p>
        </aside>
      </main>

      <footer className="site-footer">
        <p>StayLong supports preparation, coordination, and follow-through.</p>
        <p>It does not diagnose, decide eligibility, select providers, or make payments.</p>
      </footer>
    </div>
  )
}

export default App
