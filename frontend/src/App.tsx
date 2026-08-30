import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Fact = { key: string; question: string; reason: string }
type Pack = { reported_difficulty: string; assessment_discussion_topics: string[]; official_pathways: string[] }
type PlanTask = { task_id: string; title: string; description: string; status: string }
type Plan = { title: string; stated_difficulty: string; goal: string; official_pathway: string; tasks: PlanTask[] }
type Proposal = { action_type: string; revision: number; title: string; boundary_note: string }
type ActionResult = { action_type: string; action_revision: number; channel: string; payload?: Record<string, string> }
type Timeline = { event_id: string; event_type: string; details?: Record<string, string>; occurred_at?: string }
type Workflow = { case_id: string; stage: string; questions: Fact[]; pack: Pack | null; plan: Plan | null; proposed_action: Proposal | null; proposed_actions: Proposal[]; action_results: ActionResult[]; timeline: Timeline[]; integration_mode: string }
type View = 'concern' | 'intake' | 'plan' | 'emergency'
type Theme = 'original' | 'cinnamon'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const examples = [
  ['Night-time bathroom', 'I’m finding it harder to reach the bathroom safely at night. The hallway is dark and there are no rails near the toilet.'],
  ['Front steps', 'The steps at my front door are becoming difficult.'],
  ['Shower safety', 'I feel unsteady getting into and out of the shower.'],
]
const pathSteps = ['Tell us what is difficult', 'Prepare for assessment', 'Approve next steps', 'Follow through']
const assessmentStatusQuestion = 'Have you already had an aged care assessment or an occupational therapy home visit?'
const assessmentStatusOptions = [
  'Yes — aged care assessment',
  'Yes — occupational therapy home visit',
  'Yes — both',
  'No, not yet',
  'I’m not sure',
]
const quickAnswerOptions: Record<string, string[]> = {
  housing_tenure: ['I own my home', 'I rent my home', 'I’m not sure about the home yet'],
  support_contacts: ['Not right now', 'I’d like to involve someone', 'I’m not sure who to involve yet'],
}

const timelineLabels: Record<string, string> = {
  'concern.created': 'Your concern was recorded',
  'assessment.pack.prepared': 'Assessment preparation pack created',
  'approval.granted': 'You approved an action',
  'approval.declined': 'You chose to keep an action for later',
  'calendar.action.recorded': 'Calendar reminder recorded',
  'contact_draft.created': 'Contact draft created for review',
  'reminder.scheduled': 'Follow-up reminder scheduled',
  'reminder.sent': 'Follow-up reminder completed',
}

function App() {
  const [concern, setConcern] = useState('')
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [intakeQuestions, setIntakeQuestions] = useState<Fact[]>([])
  const [view, setView] = useState<View>('concern')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [busyMessage, setBusyMessage] = useState('')
  const [message, setMessage] = useState('')
  const [theme, setTheme] = useState<Theme>('original')
  const publicMode = import.meta.env.VITE_STAYLONG_API_MODE === 'public-sandbox'
  const request = useCallback(async (path: string, body?: object, method = 'POST') => {
    const url = publicMode ? `${apiBaseUrl}/v1/public${path.slice('/v1'.length)}` : `${apiBaseUrl}${path}`
    const init: RequestInit = { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined, ...(publicMode ? { credentials: 'include' } : {}) }
    const response = await fetch(url, init)
    if (!response.ok) {
      if (publicMode && response.status === 429) {
        throw new Error('This browser already has an active sandbox plan. Open an incognito window or clear this site’s cookies to start a new one.')
      }
      throw new Error('StayLong could not continue your plan. Please try again.')
    }
    return response.json() as Promise<Workflow>
  }, [publicMode])
  useEffect(() => { document.title = 'StayLong | Independent living, coordinated' }, [])
  useEffect(() => {
    if (!publicMode) return
    const caseId = sessionStorage.getItem('staylong_active_case_id')
    if (!caseId) return
    request(`/v1/workflows/${caseId}`, undefined, 'GET').then((next) => {
      setWorkflow(next)
      setIntakeQuestions(next.questions)
      setView(next.stage === 'emergency' ? 'emergency' : next.plan && next.pack ? 'plan' : 'intake')
    }).catch(() => sessionStorage.removeItem('staylong_active_case_id'))
  }, [publicMode, request])

  const step = view === 'intake' ? 2 : view === 'plan' ? (workflow?.stage === 'follow_through' || (workflow?.action_results.length ?? 0) > 0) ? 4 : 3 : 1
  const actions = workflow?.proposed_actions.length ? workflow.proposed_actions : workflow?.proposed_action ? [workflow.proposed_action] : []
  const hasPreparedPlan = Boolean(workflow?.plan && workflow.pack)
  const selectedExample = examples.find(([, summary]) => summary === concern)?.[0]

  async function start(event: FormEvent) {
    event.preventDefault(); setBusy(true); setBusyMessage('Preparing your questions'); setMessage('')
    try {
      const next = await request('/v1/workflows', { concern })
      if (publicMode) sessionStorage.setItem('staylong_active_case_id', next.case_id)
      setWorkflow(next); setIntakeQuestions(next.questions); setView(next.stage === 'emergency' ? 'emergency' : next.plan && next.pack ? 'plan' : 'intake')
      setMessage('Your concern is recorded. Nothing has been shared or booked.')
    }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Something went wrong.') } finally { setBusy(false); setBusyMessage('') }
  }

  async function prepare(event: FormEvent) {
    event.preventDefault(); if (!workflow) return; setBusy(true); setBusyMessage('Preparing your plan'); setMessage('')
    try { setWorkflow(await request(`/v1/workflows/${workflow.case_id}/answers`, { answers })); setView('plan'); setMessage('Your plan is ready to review. Nothing has been shared or booked.') }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Something went wrong.') } finally { setBusy(false); setBusyMessage('') }
  }

  async function decide(action: Proposal, decision: 'approve' | 'decline') {
    if (!workflow) return; setBusy(true); setBusyMessage('Recording your choice'); setMessage('')
    try {
      const next = await request(`/v1/workflows/${workflow.case_id}/action-decision`, { action_type: action.action_type, action_revision: action.revision, decision })
      setWorkflow(next)
      const result = next.action_results.find((item) => item.action_type === action.action_type && item.action_revision === action.revision)
      setMessage(result ? '' : 'You chose to keep this action for later. You can reconsider whenever you are ready.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Something went wrong.') } finally { setBusy(false); setBusyMessage('') }
  }

  return (
    <div className={`app-shell theme-${theme}`}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header"><a className="wordmark" href="/"><img src="/brand/staylong-lockup.svg" alt="StayLong" /></a><div className="header-tools"><p>Independent living, coordinated</p>{view === 'concern' && <StyleSwitcher theme={theme} onChange={setTheme} />}</div></header>
      <main className="workspace" id="main-content">
        <aside className="path-rail"><p className="eyebrow">Continuous Home Path</p><nav aria-label="Continuous Home Path"><ol>{pathSteps.map((item, index) => <li className={index + 1 === step ? 'active' : index + 1 < step ? 'complete' : 'upcoming'} key={item}><span className="path-number">{index + 1}</span><strong>{item}</strong></li>)}</ol></nav><p className="path-promise">You approve every external action before StayLong proceeds.</p></aside>
        <div className="task-column">
          <p className="mobile-step">Step {step} of 4</p>
          {view === 'concern' && <section className="task-panel">
            <p className="eyebrow">Start with what you notice</p>
            <h1>What would make home easier today?</h1>
            <p className="task-intro">Choose an example, or tell us in your own words.</p>
            <form onSubmit={start}>
              <div className="conversation-preview" aria-live="polite">
                <p className="assistant-bubble">Tell StayLong what has become harder at home.</p>
              </div>
              <div className="example-options">{examples.map(([label, summary]) => <button aria-pressed={concern === summary} className="example-option" key={label} onClick={() => setConcern(summary)} type="button">{label}</button>)}</div>
              {selectedExample && <div className="selected-example" role="status"><p>You chose: {selectedExample}</p><p>We’ve added a starting point below — change the words so they sound like you.</p></div>}
              <div className="input-group"><label htmlFor="concern">Describe what is becoming difficult</label><p className="field-help">No example fits? That’s okay — describe what you noticed below.</p><textarea aria-describedby="concern-help" id="concern" onChange={(event) => setConcern(event.target.value)} required value={concern} /><span className="sr-only" id="concern-help">You can describe a different concern in your own words.</span></div>
              <div className="flow-actions"><button className="primary-action" disabled={busy || !concern.trim()}>{busy ? 'Preparing your questions…' : 'Start my plan'}</button>{workflow && <button className="secondary-action" onClick={() => setView(hasPreparedPlan ? 'plan' : 'intake')} type="button">{hasPreparedPlan ? 'Return to my plan' : 'Return to preparation'}</button>}</div>
            </form>
          </section>}
          {view === 'emergency' && <section className="task-panel emergency-panel"><h1>Call Triple Zero (000) now</h1><p>If anyone may be in immediate danger, call 000. StayLong will not prepare or run a plan for an emergency.</p></section>}
          {view === 'intake' && workflow && <section className="task-panel"><p className="eyebrow">Prepare with confidence</p><h1>A few details will help prepare your plan</h1><form onSubmit={prepare}>{intakeQuestions.map((question) => <IntakeQuestion key={question.key} question={question} value={answers[question.key] ?? ''} onChange={(value) => setAnswers({ ...answers, [question.key]: value })} />)}<div className="flow-actions"><button className="secondary-action" onClick={() => setView('concern')} type="button">Back to my concern</button>{workflow.stage === 'intake' ? <button className="primary-action" disabled={busy}>{busy ? 'Preparing your plan…' : 'Prepare my plan'}</button> : <button className="primary-action" onClick={() => setView('plan')} type="button">Return to my plan</button>}</div></form></section>}
          {view === 'plan' && workflow?.plan && workflow.pack && <PlanBoard actions={actions} busy={busy} integrationMode={workflow.integration_mode} onBackToAssessment={() => setView('intake')} onDecision={decide} pack={workflow.pack} plan={workflow.plan} results={workflow.action_results} stage={workflow.stage} timeline={workflow.timeline} />}
          {busyMessage && <p className="loading-status" role="status" aria-label={busyMessage}>{busyMessage}…</p>}
          {message && <p className="global-status has-message" role="status">{message}</p>}
        </div>
      </main>
      <footer className="site-footer"><p>StayLong supports preparation, coordination, and follow-through.</p><p>It does not diagnose, decide eligibility, select providers, or make payments.</p><p className="emergency-note">If there is immediate danger, call Triple Zero (000).</p></footer>
    </div>
  )
}

function StyleSwitcher({ theme, onChange }: { theme: Theme; onChange: (theme: Theme) => void }) {
  return <div aria-label="Choose visual style" className="style-switcher" role="group"><span>Style</span><button aria-pressed={theme === 'original'} onClick={() => onChange('original')} type="button">Sage</button><button aria-pressed={theme === 'cinnamon'} onClick={() => onChange('cinnamon')} type="button">Rose</button></div>
}

function IntakeQuestion({ question, value, onChange }: { question: Fact; value: string; onChange: (value: string) => void }) {
  if (question.key === 'assessment_status') {
    return <fieldset className="input-group choice-group"><legend>{assessmentStatusQuestion}</legend><div className="choice-options">{assessmentStatusOptions.map((option) => <label className="choice-option" key={option}><input checked={value === option} name={question.key} onChange={() => onChange(option)} required type="radio" value={option} /><span>{option}</span></label>)}</div><p className="field-help">{question.reason}</p></fieldset>
  }
  const options = quickAnswerOptions[question.key]
  if (options) {
    return <fieldset className="input-group choice-group"><legend>{question.question}</legend><div className="choice-options">{options.map((option) => <label className="choice-option" key={option}><input checked={value === option} name={question.key} onChange={() => onChange(option)} required type="radio" value={option} /><span>{option}</span></label>)}</div><p className="field-help">{question.reason}</p></fieldset>
  }
  return <div className="input-group"><label htmlFor={question.key}>{question.question}</label><input id={question.key} onChange={(event) => onChange(event.target.value)} required value={value} /><p className="field-help">{question.reason}</p></div>
}

function PlanBoard({ plan, pack, actions, results, timeline, busy, integrationMode, stage, onBackToAssessment, onDecision }: { plan: Plan; pack: Pack; actions: Proposal[]; results: ActionResult[]; timeline: Timeline[]; busy: boolean; integrationMode: string; stage?: string; onBackToAssessment: () => void; onDecision: (action: Proposal, decision: 'approve' | 'decline') => void }) {
  const isFollowThrough = stage === 'follow_through' || results.length > 0
  const declinedTypes = new Set(
    timeline
      .filter((e) => e.event_type === 'approval.declined')
      .map((e) => e.details?.action_type)
      .filter(Boolean),
  )
  const allResolved = actions.length > 0 && actions.every((a) => results.some((r) => r.action_type === a.action_type) || declinedTypes.has(a.action_type))
  const allActionsComplete = actions.length > 0 && actions.every((action) => results.some((result) => result.action_type === action.action_type && result.action_revision === action.revision))
  const integrationLabel = integrationMode === 'google_oauth' ? 'Connected Google actions' : 'Actions you control'
  const actionSectionTitle = isFollowThrough ? (allResolved ? 'Your approved steps & records' : 'Actions and follow-through') : 'Optional help when you want it'
  const officialPathway = pack.official_pathways[0] ?? plan.official_pathway

  function revealPreparationPack() {
    const details = document.getElementById('plan-details') as HTMLDetailsElement | null
    if (details) details.open = true
    document.getElementById('preparation-pack')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <section className="plan-board">
      {isFollowThrough && (
        <div className="follow-through-banner" role="status">
          <p className="eyebrow">Step 4 &bull; Follow through</p>
          <h2>Your plan is underway</h2>
          <p>Approved actions are recorded below. You retain full control &mdash; nothing is shared or booked without your explicit approval.</p>
        </div>
      )}
      <div className="plan-heading">
        <p className="eyebrow">A plan you control</p>
        <h1>{plan.title}</h1>
        <p>{plan.goal}</p>
      </div>
      <section className="concern-card">
        <p className="eyebrow">Recorded concern</p>
        <p>{plan.stated_difficulty}</p>
      </section>
      <details className="plan-details" data-testid="plan-details" id="plan-details" open>
        <summary>Plan and preparation notes</summary>
        <section className="task-list">
          <h2>Your practical next steps</h2>
          {plan.tasks.map((task, index) => (
            <article className="plan-task" key={task.task_id}>
              <span>{index + 1}</span>
              <div>
                <h3>{task.title}</h3>
                <p>{task.description}</p>
                {task.status === 'completed' ? (
                  <small className="status-completed">&check; Completed in plan</small>
                ) : (
                  <TaskSupport task={task} officialPathway={officialPathway} onReviewPack={revealPreparationPack} />
                )}
              </div>
            </article>
          ))}
        </section>
        <section className="pack-card" id="preparation-pack" tabIndex={-1}>
          <h2>What to prepare for your assessment</h2>
          <p>{pack.reported_difficulty}</p>
          {pack.assessment_discussion_topics && pack.assessment_discussion_topics.length > 0 && (
            <ul className="pack-topics">
              {pack.assessment_discussion_topics.map((topic, index) => (
                <li key={index}>{topic}</li>
              ))}
            </ul>
          )}
          <a href={officialPathway}>Open My Aged Care</a>
        </section>
        {timeline.length > 0 && (
          <section className="timeline-card">
            <h2>Plan record</h2>
            <ol aria-label="Plan timeline">
              {timeline.map((event) => (
                <li key={event.event_id}>
                  <strong>{timelineLabels[event.event_type] ?? event.event_type}</strong>
                  <span className="event-type-tag">{event.event_type}</span>
                </li>
              ))}
            </ol>
          </section>
        )}
      </details>
      <section className="action-area">
        <p className="eyebrow">{integrationLabel}</p>
        <h2>{actionSectionTitle}</h2>
        <p className="action-intro">These choices stay in your plan until you decide.</p>
        {actions.map((action) => (
          <ActionCard
            action={action}
            busy={busy}
            isDeclined={declinedTypes.has(action.action_type) && !results.some((r) => r.action_type === action.action_type)}
            key={action.action_type}
            onDecision={onDecision}
            result={results.find((item) => item.action_type === action.action_type && item.action_revision === action.revision)}
          />
        ))}
      </section>
      {allActionsComplete && (
        <section className="completion-card" aria-labelledby="completion-heading">
          <p className="eyebrow">Follow through</p>
          <h2 id="completion-heading">Your plan is ready to continue</h2>
          <p>Both actions are recorded in this sandbox plan. Nothing was sent or booked.</p>
          <p className="completion-next">When you are ready, take these notes to your aged-care or occupational-therapy conversation.</p>
          <div className="flow-actions">
            <button className="secondary-action" onClick={revealPreparationPack} type="button">Review preparation pack</button>
            <a className="primary-action link-action" href={officialPathway}>Open My Aged Care</a>
          </div>
        </section>
      )}
      <div className="flow-actions plan-navigation">
        <button className="secondary-action" onClick={onBackToAssessment} type="button">Back to assessment</button>
      </div>
    </section>
  )
}

function TaskSupport({ task, officialPathway, onReviewPack }: { task: PlanTask; officialPathway: string; onReviewPack: () => void }) {
  const taskId = task.task_id
  if (taskId === 'assessment' || taskId === 'arrange-assessment') {
    return <div className="task-support"><a href={officialPathway}>Open My Aged Care pathway</a><small>Use this official service when you decide you are ready. StayLong does not submit an assessment.</small></div>
  }
  if (taskId === 'notes' || taskId === 'prepare-notes') {
    return <div className="task-support"><button className="text-action" onClick={onReviewPack} type="button">Review your notes in the preparation pack</button><small>Check the difficulty, what happens at night, and what would help before you talk with a professional.</small></div>
  }
  if (taskId === 'permission' || taskId === 'confirm-home-access') {
    return <AccessChecklist />
  }
  return <div className="task-support"><small>{task.status === 'ready' ? 'Your next step is ready when you choose to continue.' : task.status}</small></div>
}

function AccessChecklist() {
  const [open, setOpen] = useState(false)
  return <details aria-label="Access checklist" className="task-support task-checklist" onToggle={(event) => setOpen(event.currentTarget.open)}><summary>{open ? 'Hide access checklist' : 'Show access checklist'}</summary><ul><li>Is the home owned, rented, or in a managed building?</li><li>Would a landlord, building manager, or trusted supporter need to be involved?</li><li>What access details should you confirm before any changes?</li></ul></details>
}

function ActionCard({ action, result, isDeclined, busy, onDecision }: { action: Proposal; result?: ActionResult; isDeclined?: boolean; busy: boolean; onDecision: (action: Proposal, decision: 'approve' | 'decline') => void }) {
  const [copied, setCopied] = useState(false)

  function copyDraft(text: string) {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }

  if (result) {
    const isDraft = action.action_type === 'contact_draft.create'
    const draftPayload = result.payload
    return (
      <article className="action-card completed">
        <h3>{action.title}</h3>
        <p className="action-state">Completed — recorded in this sandbox plan</p>
        <p className="action-result">{resultMessage(result)}</p>
        <p className="action-next-step">{resultNextStep(result)}</p>
        {isDraft && draftPayload?.body && (
          <div className="draft-preview-box">
            <div className="draft-preview-header">
              <p className="eyebrow">Unsent draft preview</p>
              <button
                className="secondary-action draft-copy-btn"
                onClick={() => copyDraft(draftPayload.body ?? '')}
                type="button"
              >
                {copied ? 'Copied to clipboard!' : 'Copy draft text'}
              </button>
            </div>
            {draftPayload.subject && (
              <p className="draft-subject"><strong>Subject:</strong> {draftPayload.subject}</p>
            )}
            <pre className="draft-body-content">{draftPayload.body}</pre>
            <small className="draft-safety-note">Sandbox draft &mdash; ready for your review, never sent automatically.</small>
          </div>
        )}
      </article>
    )
  }

  if (isDeclined) {
    return (
      <article className="action-card deferred">
        <h3>{action.title}</h3>
        <p className="action-state">Kept for later &mdash; no action was taken.</p>
        <p>You can reconsider and approve this step whenever you are ready.</p>
        <div className="action-buttons">
          <button className="secondary-action" disabled={busy} onClick={() => onDecision(action, 'approve')}>
            Reconsider and approve
          </button>
        </div>
      </article>
    )
  }

  const calendar = action.action_type === 'calendar.create'
  return (
    <article className="action-card">
      <h3>{calendar ? 'Add a reminder to this plan' : 'Create a contact draft to review'}</h3>
      <p>{calendar ? 'Keep the assessment preparation in your StayLong plan. It will not add anything to an external calendar.' : 'Create a private draft first. You can read it here and it will not be sent.'}</p>
      <p className="action-boundary">{action.boundary_note}</p>
      <div className="action-buttons">
        <button className="primary-action" disabled={busy} onClick={() => onDecision(action, 'approve')}>
          {busy ? 'Recording your choice…' : calendar ? 'Add reminder to my plan' : 'Create draft to review'}
        </button>
        <button aria-label={`Keep ${action.title} for later`} className="secondary-action" disabled={busy} onClick={() => onDecision(action, 'decline')}>
          Not now
        </button>
      </div>
    </article>
  )
}

function resultMessage(result: ActionResult) {
  return result.action_type === 'calendar.create'
    ? result.channel === 'google_calendar'
      ? 'Calendar event created'
      : 'Reminder added to your plan — no external calendar event was created.'
    : 'Contact draft created for your review — it has not been sent.'
}

function resultNextStep(result: ActionResult) {
  return result.action_type === 'calendar.create'
    ? 'You can use your assessment notes during your My Aged Care discussion.'
    : 'You can review and share the draft when you are ready.'
}

export default App


