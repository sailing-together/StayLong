import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type CaseRecord = { case_id: string; status: string }
type Concern = { concern_id: string; case_id: string; summary: string }
type RequestState = 'idle' | 'saving' | 'success' | 'error'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''

function App() {
  const [accessToken, setAccessToken] = useState('')
  const [concernSummary, setConcernSummary] = useState('')
  const [caseRecord, setCaseRecord] = useState<CaseRecord | null>(null)
  const [concerns, setConcerns] = useState<Concern[]>([])
  const [requestState, setRequestState] = useState<RequestState>('idle')
  const [message, setMessage] = useState('')

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
        throw new Error('StayLong could not create this household case.')
      }

      const createdCase = (await response.json()) as CaseRecord
      const concernsResponse = await fetch(
        `${apiBaseUrl}/v1/cases/${createdCase.case_id}/concerns`,
        { headers: { Authorization: `Bearer ${accessToken}` } },
      )
      if (!concernsResponse.ok) {
        throw new Error('The household was created, but its case path could not load.')
      }

      setCaseRecord(createdCase)
      setConcerns((await concernsResponse.json()) as Concern[])
      setRequestState('success')
      setMessage('Case created. The first practical concern is now on its coordination path.')
    } catch (error) {
      setRequestState('error')
      setMessage(error instanceof Error ? error.message : 'Something went wrong.')
    }
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="wordmark" href="#workspace" aria-label="StayLong home">
          Stay<span>Long</span>
        </a>
        <p className="header-note">Independent living, coordinated with care.</p>
      </header>

      <section className="intro" aria-labelledby="workspace-title">
        <p className="eyebrow">Family workspace</p>
        <h1 id="workspace-title">Start with what is making home harder.</h1>
        <p className="intro-copy">
          StayLong helps an older person living alone turn a home concern into an
          organised, consent-led coordination path. Invite a trusted supporter
          only when you choose. It does not diagnose, decide eligibility, choose
          providers, or make payments.
        </p>
      </section>

      <section className="workspace-grid" id="workspace">
        <form className="surface concern-form" onSubmit={createCase}>
          <div className="surface-heading">
            <p className="eyebrow">01 · Create a household case</p>
            <h2>What is making home harder?</h2>
          </div>

          <label htmlFor="access-token">Demo access token</label>
          <input
            id="access-token"
            type="password"
            value={accessToken}
            onChange={(event) => setAccessToken(event.target.value)}
            autoComplete="off"
            required
          />
          <p className="field-help">Held only while this page is open.</p>

          <label htmlFor="concern-summary">What is making home harder?</label>
          <textarea
            id="concern-summary"
            value={concernSummary}
            onChange={(event) => setConcernSummary(event.target.value)}
            placeholder="For example: getting safely to the bathroom at night is becoming difficult."
            rows={5}
            required
          />

          <div className="consent-note">
            <span aria-hidden="true">✦</span>
            <p>
              You choose whether to invite a trusted supporter. External sharing,
              bookings, and costs always need your approval.
            </p>
          </div>

          <button type="submit" disabled={requestState === 'saving'}>
            {requestState === 'saving' ? 'Creating case…' : 'Create household case'}
          </button>
          {message && (
            <p className={`form-message ${requestState}`} role="status">
              {message}
            </p>
          )}
        </form>

        <aside className="surface case-path" aria-labelledby="case-path-title">
          <div className="surface-heading">
            <p className="eyebrow">02 · Case path</p>
            <h2 id="case-path-title">What StayLong knows</h2>
          </div>

          {caseRecord ? (
            <div className="case-details">
              <div className="case-identity">
                <span className="case-dot" aria-hidden="true" />
                <div>
                  <p className="overline">Active case · {caseRecord.status}</p>
                  <h3>Practical concern recorded</h3>
                </div>
              </div>
              <p>{concerns[0]?.summary ?? 'No concern is recorded yet.'}</p>
              <ol className="path-list">
                <li className="path-current">
                  <span>1</span>
                  <div>
                    <strong>Capture the practical concern</strong>
                    <p>
                      {concerns.length
                        ? `${concerns.length} recorded concern${concerns.length === 1 ? '' : 's'}.`
                        : 'No concern is recorded yet.'}
                    </p>
                  </div>
                </li>
                <li>
                  <span>2</span>
                  <div>
                    <strong>Prepare for the right human assessment</strong>
                    <p>Only after the family adds the relevant facts.</p>
                  </div>
                </li>
                <li>
                  <span>3</span>
                  <div>
                    <strong>Coordinate approved follow-up</strong>
                    <p>No provider, cost, or booking is assumed here.</p>
                  </div>
                </li>
              </ol>
            </div>
          ) : (
            <div className="empty-path">
              <div className="empty-mark" aria-hidden="true">↗</div>
              <h3>Your case path will appear here.</h3>
              <p>
                Start with a concern you want help coordinating. StayLong will
                show only the information you supply or the service returns.
              </p>
            </div>
          )}
        </aside>
      </section>

      <footer>
        <p>
          StayLong supports preparation, coordination, and follow-through — not
          clinical or funding decisions.
        </p>
      </footer>
    </main>
  )
}

export default App
