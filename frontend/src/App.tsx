import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type CaseRecord = { case_id: string; status: string }
type Concern = { concern_id: string; case_id: string; summary: string }
type RequestState = 'idle' | 'saving' | 'success' | 'error'

type Example = {
  id: string
  label: string
  summary: string
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

const examples: Example[] = [
  {
    id: 'night-bathroom',
    label: 'Night-time bathroom',
    summary:
      'I’m finding it harder to reach the bathroom safely at night. The hallway is dark and there are no rails near the toilet.',
  },
  {
    id: 'front-steps',
    label: 'Front steps',
    summary:
      'The steps at my front door are becoming difficult. I would like help understanding what could make entering and leaving home easier.',
  },
  {
    id: 'shower-safety',
    label: 'Shower safety',
    summary:
      'I feel unsteady getting into and out of the shower. I would like help preparing to discuss safer options at an assessment.',
  },
]

const pathSteps = [
  'Tell us what is difficult',
  'Prepare for assessment',
  'Approve next steps',
  'Follow through',
]

function App() {
  const [concernSummary, setConcernSummary] = useState('')
  const [selectedExample, setSelectedExample] = useState<string | null>(null)
  const [caseRecord, setCaseRecord] = useState<CaseRecord | null>(null)
  const [concerns, setConcerns] = useState<Concern[]>([])
  const [requestState, setRequestState] = useState<RequestState>('idle')
  const [message, setMessage] = useState('')
  const concernInput = useRef<HTMLTextAreaElement>(null)
  const recordedConcernSection = useRef<HTMLElement>(null)

  useEffect(() => {
    document.title = 'StayLong | Independent living, coordinated'
  }, [])

  const recordedConcern = concerns[0]?.summary
  const hasCase = Boolean(caseRecord && recordedConcern)
  const activeStep = hasCase ? 2 : 1

  useEffect(() => {
    if (hasCase) recordedConcernSection.current?.focus()
  }, [hasCase])

  useEffect(() => {
    if (!hasCase && requestState === 'idle' && concernSummary) concernInput.current?.focus()
  }, [concernSummary, hasCase, requestState])

  function chooseExample(example: Example) {
    setSelectedExample(example.id)
    setConcernSummary(example.summary)
    concernInput.current?.focus()
  }

  function updateConcern(summary: string) {
    setConcernSummary(summary)
    const selected = examples.find((example) => example.id === selectedExample)
    if (selected && summary !== selected.summary) setSelectedExample(null)
  }

  function reviewRecordedConcern() {
    recordedConcernSection.current?.focus()
    recordedConcernSection.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  }

  function startCorrection() {
    setConcernSummary(recordedConcern ?? concernSummary)
    setCaseRecord(null)
    setConcerns([])
    setRequestState('idle')
    setMessage('')
    setSelectedExample(null)
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
        },
        body: JSON.stringify({ summary: concernSummary }),
      })
      if (!response.ok) {
        throw new Error('StayLong could not start your plan. Please check the demo connection and try again.')
      }

      const createdCase = (await response.json()) as CaseRecord
      const concernsResponse = await fetch(
        `${apiBaseUrl}/v1/cases/${createdCase.case_id}/concerns`,
      )
      if (!concernsResponse.ok) {
        throw new Error('Your plan was started, but StayLong could not load the concern yet.')
      }

      setCaseRecord(createdCase)
      setConcerns((await concernsResponse.json()) as Concern[])
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

      <aside className="emergency-bar" id="urgent-help" aria-label="Emergency guidance">
        If anyone is in immediate danger, call 000.
      </aside>

      <header className="site-header">
        <a className="wordmark" href="#main-content" aria-label="StayLong home">
          <img src="/brand/staylong-lockup.svg" alt="StayLong" />
        </a>
        <p>Independent living, coordinated</p>
      </header>

      <main className="workspace" id="main-content">
        <div className="mobile-step" aria-label="Current plan step">
          <strong>Step {activeStep} of 4</strong>
          <span>{pathSteps[activeStep - 1]}</span>
        </div>

        <aside className="path-rail">
          <p className="eyebrow">Continuous Home Path</p>
          <nav aria-label="Continuous Home Path">
            <ol>
              {pathSteps.map((step, index) => {
                const stepNumber = index + 1
                const state = stepNumber === activeStep ? 'active' : stepNumber < activeStep ? 'complete' : 'upcoming'
                return (
                  <li className={state} key={step} aria-current={state === 'active' ? 'step' : undefined}>
                    <span className="path-number" aria-hidden="true">{stepNumber}</span>
                    <span>
                      <strong>{step}</strong>
                      {state === 'active' && <small>Current step</small>}
                    </span>
                  </li>
                )
              })}
            </ol>
          </nav>
          <p className="path-promise">You approve every external action before StayLong proceeds.</p>
        </aside>

        <div className="task-column">
          {!hasCase ? (
            <section className="task-panel" aria-labelledby="page-title">
              <h1 id="page-title">What would make home easier today?</h1>
              <p className="task-intro">
                Choose a common example or describe what is becoming difficult in your own words.
              </p>

              <form onSubmit={createCase}>
                <fieldset className="example-fieldset">
                  <legend>Try an example</legend>
                  <div className="example-options">
                    {examples.map((example) => (
                      <button
                        key={example.id}
                        type="button"
                        className="example-option"
                        aria-pressed={selectedExample === example.id}
                        onClick={() => chooseExample(example)}
                      >
                        {example.label}
                      </button>
                    ))}
                  </div>
                </fieldset>

                <div className="input-group">
                  <label htmlFor="concern-summary">Describe what is becoming difficult</label>
                  <textarea
                    ref={concernInput}
                    id="concern-summary"
                    value={concernSummary}
                    onChange={(event) => updateConcern(event.target.value)}
                    placeholder="For example: Getting to the bathroom at night is becoming difficult."
                    rows={4}
                    maxLength={2000}
                    required
                  />
                  <p className="field-help">Only include information you are comfortable recording.</p>
                </div>

                <div className="form-actions">
                  <button
                    className="primary-action"
                    type="submit"
                    disabled={requestState === 'saving' || !concernSummary.trim()}
                  >
                    {requestState === 'saving' ? 'Starting your plan…' : 'Start my plan'}
                  </button>
                  <p><strong>You stay in control.</strong> Nothing is shared, booked, or paid for without your approval.</p>
                </div>

              </form>
            </section>
          ) : (
            <section
              ref={recordedConcernSection}
              className="task-panel recorded-concern"
              aria-labelledby="recorded-concern-title"
              tabIndex={-1}
            >
              <p className="eyebrow">Prepared from your words</p>
              <h1 id="recorded-concern-title">StayLong understood this concern</h1>
              <blockquote>{recordedConcern}</blockquote>
              <p className="case-fact">Case status: {caseRecord?.status}</p>
              <p>Nothing has been shared or booked. Check this before StayLong prepares any follow-up.</p>
              <div className="recorded-actions">
                <button className="primary-action" type="button" onClick={reviewRecordedConcern}>
                  Review what StayLong understood
                </button>
                <button className="secondary-action" type="button" onClick={startCorrection}>
                  Start again with a correction
                </button>
              </div>
            </section>
          )}

          <p className={`global-status ${message ? 'has-message' : ''} ${requestState}`} role="status" aria-live="polite">
            {message}
          </p>

          <section className="plan-summary" aria-labelledby="plan-summary-title">
            <p className="eyebrow" id="plan-summary-title">Your plan summary</p>
            <dl>
              <div><dt>Status</dt><dd>{hasCase ? 'Started' : 'Not started'}</dd></div>
              <div><dt>Next</dt><dd>{hasCase ? 'Check the recorded concern' : 'Describe what is becoming difficult'}</dd></div>
              <div><dt>Supporter</dt><dd>No one invited</dd></div>
            </dl>
          </section>
        </div>
      </main>

      <footer className="site-footer">
        <p>StayLong supports preparation, coordination, and follow-through.</p>
        <p>It does not diagnose, decide eligibility, select providers, or make payments.</p>
      </footer>
    </div>
  )
}

export default App
