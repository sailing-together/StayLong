import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type Fact = { key: string; question: string; reason: string }
type Pack = { reported_difficulty: string; assessment_discussion_topics: string[]; official_pathways: string[] }
type PlanTask = { task_id: string; title: string; description: string; status: string }
type Plan = { title: string; stated_difficulty: string; goal: string; official_pathway: string; tasks: PlanTask[] }
type Proposal = { action_type: string; revision: number; title: string; boundary_note: string }
type ActionResult = { action_type: string; action_revision: number; channel: string }
type Timeline = { event_id: string; event_type: string }
type Workflow = { case_id: string; stage: string; questions: Fact[]; pack: Pack | null; plan: Plan | null; proposed_action: Proposal | null; proposed_actions: Proposal[]; action_results: ActionResult[]; timeline: Timeline[]; integration_mode: string }
type View = 'concern' | 'intake' | 'plan' | 'emergency'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const examples = [
  ['Night-time bathroom', 'I’m finding it harder to reach the bathroom safely at night. The hallway is dark and there are no rails near the toilet.'],
  ['Front steps', 'The steps at my front door are becoming difficult.'],
  ['Shower safety', 'I feel unsteady getting into and out of the shower.'],
]
const pathSteps = ['Tell us what is difficult', 'Prepare for assessment', 'Approve next steps', 'Follow through']

function App() {
  const [concern, setConcern] = useState('')
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [intakeQuestions, setIntakeQuestions] = useState<Fact[]>([])
  const [view, setView] = useState<View>('concern')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  useEffect(() => { document.title = 'StayLong | Independent living, coordinated' }, [])
  const step = view === 'intake' ? 2 : view === 'plan' ? workflow?.stage === 'follow_through' ? 4 : 3 : 1
  const actions = workflow?.proposed_actions.length ? workflow.proposed_actions : workflow?.proposed_action ? [workflow.proposed_action] : []
  const selectedExample = examples.find(([, summary]) => summary === concern)?.[0]
  const publicMode = import.meta.env.VITE_STAYLONG_API_MODE === 'public-sandbox'
  async function request(path: string, body?: object) {
    const url = publicMode ? `${apiBaseUrl}/v1/public${path.slice('/v1'.length)}` : `${apiBaseUrl}${path}`
    const init: RequestInit = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined, ...(publicMode ? { credentials: 'include' } : {}) }
    const response = await fetch(url, init)
    if (!response.ok) throw new Error('StayLong could not continue your plan. Please try again.')
    return response.json() as Promise<Workflow>
  }
  async function start(event: FormEvent) {
    event.preventDefault(); setBusy(true)
    try {
      const next = await request('/v1/workflows', { concern })
      setWorkflow(next); setIntakeQuestions(next.questions); setView(next.stage === 'emergency' ? 'emergency' : next.plan && next.pack ? 'plan' : 'intake')
      setMessage('Your concern is recorded. Nothing has been shared or booked.')
    }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Something went wrong.') } finally { setBusy(false) }
  }
  async function prepare(event: FormEvent) {
    event.preventDefault(); if (!workflow) return; setBusy(true)
    try { setWorkflow(await request(`/v1/workflows/${workflow.case_id}/answers`, { answers })); setView('plan'); setMessage('Your plan is ready to review. Nothing has been shared or booked.') }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Something went wrong.') } finally { setBusy(false) }
  }
  async function decide(action: Proposal, decision: 'approve' | 'decline') {
    if (!workflow) return; setBusy(true)
    try {
      const next = await request(`/v1/workflows/${workflow.case_id}/action-decision`, { action_type: action.action_type, action_revision: action.revision, decision })
      setWorkflow(next)
      const result = next.action_results.find((item) => item.action_type === action.action_type && item.action_revision === action.revision)
      setMessage(result ? '' : 'This action is waiting for you.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Something went wrong.') } finally { setBusy(false) }
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header"><a className="wordmark" href="/"><img src="/brand/staylong-lockup.svg" alt="StayLong" /></a><p>Independent living, coordinated</p></header>
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
              <div className="flow-actions"><button className="primary-action" disabled={busy || !concern.trim()}>Start my plan</button>{workflow && <button className="secondary-action" onClick={() => setView('intake')} type="button">Return to preparation</button>}</div>
            </form>
          </section>}
          {view === 'emergency' && <section className="task-panel emergency-panel"><h1>Call Triple Zero (000) now</h1><p>If anyone may be in immediate danger, call 000. StayLong will not prepare or run a plan for an emergency.</p></section>}
          {view === 'intake' && workflow && <section className="task-panel"><p className="eyebrow">Prepare with confidence</p><h1>A few details will help prepare your plan</h1><form onSubmit={prepare}>{intakeQuestions.map((question) => <div className="input-group" key={question.key}><label htmlFor={question.key}>{question.question}</label><input id={question.key} onChange={(event) => setAnswers({ ...answers, [question.key]: event.target.value })} required value={answers[question.key] ?? ''} /><p className="field-help">{question.reason}</p></div>)}<div className="flow-actions"><button className="secondary-action" onClick={() => setView('concern')} type="button">Back to my concern</button>{workflow.stage === 'intake' ? <button className="primary-action" disabled={busy}>Prepare my plan</button> : <button className="primary-action" onClick={() => setView('plan')} type="button">Return to my plan</button>}</div></form></section>}
          {view === 'plan' && workflow?.plan && workflow.pack && <PlanBoard actions={actions} busy={busy} integrationMode={workflow.integration_mode} onBackToAssessment={() => setView('intake')} onDecision={decide} pack={workflow.pack} plan={workflow.plan} results={workflow.action_results} timeline={workflow.timeline} />}
          {message && <p className="global-status" role="status">{message}</p>}
        </div>
      </main>
      <footer className="site-footer"><p>StayLong supports preparation, coordination, and follow-through.</p><p>It does not diagnose, decide eligibility, select providers, or make payments.</p><p className="emergency-note">If there is immediate danger, call Triple Zero (000).</p></footer>
    </div>
  )
}

function PlanBoard({ plan, pack, actions, results, timeline, busy, integrationMode, onBackToAssessment, onDecision }: { plan: Plan; pack: Pack; actions: Proposal[]; results: ActionResult[]; timeline: Timeline[]; busy: boolean; integrationMode: string; onBackToAssessment: () => void; onDecision: (action: Proposal, decision: 'approve' | 'decline') => void }) {
  const integrationLabel = integrationMode === 'google_oauth' ? 'Connected Google actions' : 'Actions you control'
  return <section className="plan-board"><div className="plan-heading"><p className="eyebrow">A plan you control</p><h1>{plan.title}</h1><p>{plan.goal}</p></div><section className="concern-card"><p className="eyebrow">What StayLong heard</p><p>{plan.stated_difficulty}</p></section><section className="task-list"><h2>Your practical next steps</h2>{plan.tasks.map((task, index) => <article className="plan-task" key={task.task_id}><span>{index + 1}</span><div><h3>{task.title}</h3><p>{task.description}</p><small>{task.status === 'ready' ? 'Ready when you are' : task.status}</small></div></article>)}</section><section className="pack-card"><h2>Assessment preparation</h2><p>{pack.reported_difficulty}</p><a href={pack.official_pathways[0] ?? plan.official_pathway}>Open My Aged Care</a></section><section className="action-area"><p className="eyebrow">{integrationLabel}</p><h2>Actions waiting for you</h2>{actions.map((action) => <ActionCard action={action} busy={busy} key={action.action_type} onDecision={onDecision} result={results.find((item) => item.action_type === action.action_type && item.action_revision === action.revision)} />)}</section><div className="flow-actions plan-navigation"><button className="secondary-action" onClick={onBackToAssessment} type="button">Back to assessment</button></div>{timeline.length > 0 && <section className="timeline-card"><h2>Plan record</h2><ol aria-label="Plan timeline">{timeline.map((event) => <li key={event.event_id}>{event.event_type}</li>)}</ol></section>}</section>
}

function ActionCard({ action, result, busy, onDecision }: { action: Proposal; result?: ActionResult; busy: boolean; onDecision: (action: Proposal, decision: 'approve' | 'decline') => void }) {
  if (result) return <article className="action-card completed"><h3>{action.title}</h3><p>{resultMessage(result)}</p></article>
  const calendar = action.action_type === 'calendar.create'
  return <article className="action-card"><h3>{action.title}</h3><p>You choose before anything happens.</p><p className="action-state">{calendar ? 'Calendar reminder waiting for approval' : 'Contact draft waiting for approval'}</p><div className="action-buttons"><button className="primary-action" disabled={busy} onClick={() => onDecision(action, 'approve')}>{calendar ? 'Add assessment reminder to calendar' : 'Create contact draft for review'}</button><button aria-label={`Keep ${action.title} for later`} className="secondary-action" disabled={busy} onClick={() => onDecision(action, 'decline')}>Not now</button></div></article>
}

function resultMessage(result: ActionResult) { return result.action_type === 'calendar.create' ? result.channel === 'google_calendar' ? 'Calendar event created' : 'Reminder added to your plan' : 'Contact draft created for your review — it has not been sent.' }

export default App
