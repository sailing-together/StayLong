import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const concern = 'Getting to the bathroom at night is difficult.'
const questions = [
  { key: 'assessment_status', question: 'Has a My Aged Care assessment been arranged?', reason: 'This helps prepare the right next step.' },
  { key: 'housing_tenure', question: 'Is the home owned or rented?', reason: 'Permission requirements may affect planning.' },
  { key: 'support_contacts', question: 'Would you like to involve anyone now?', reason: 'StayLong only shares information when invited.' },
]

function workflow(stage: string, overrides: Record<string, unknown> = {}) {
  return {
    case_id: 'case-123',
    stage,
    questions: stage === 'intake' ? questions : [],
    pack: null,
    plan: null,
    proposed_action: null,
    proposed_actions: [],
    action_result: null,
    action_results: [],
    integration_mode: 'sandbox',
    reminder: null,
    timeline: [{ event_id: 'event-1', event_type: 'concern.created', details: {}, occurred_at: '2026-08-23T10:00:00Z' }],
    ...overrides,
  }
}

const prepared = workflow('awaiting_approval', {
  pack: {
    concern_summary: concern,
    reported_difficulty: 'The hallway is dark and there are no rails near the toilet.',
    information_to_confirm: [],
    assessment_discussion_topics: ['Describe the night-time bathroom route.'],
    official_pathways: ['https://www.myagedcare.gov.au/'],
    proposed_next_step: 'prepare_assessment_pack',
    boundary_note: 'StayLong prepares and coordinates information only.',
  },
  plan: {
    title: 'Your Home Independence Plan',
    stated_difficulty: 'The hallway is dark and there are no rails near the toilet.',
    goal: 'Stay independent at home with a safer night-time bathroom routine.',
    official_pathway: 'https://www.myagedcare.gov.au/',
    tasks: [
      { task_id: 'assessment', title: 'Arrange a My Aged Care assessment', description: 'Use your preparation pack to explain what is difficult.', owner: 'You', due_at: '2026-08-25T09:00:00Z', status: 'ready', blocker: null },
      { task_id: 'notes', title: 'Prepare your assessment notes', description: 'Keep the practical details ready for the assessment.', owner: 'You', due_at: '2026-08-25T09:00:00Z', status: 'ready', blocker: null },
      { task_id: 'permission', title: 'Confirm home access or permission', description: 'Confirm whether a landlord or building manager needs to be involved.', owner: 'You', due_at: '2026-08-25T09:00:00Z', status: 'ready', blocker: null },
    ],
  },
  proposed_action: {
    action_type: 'calendar.create', revision: 1, title: 'Review your assessment preparation pack',
    starts_at: '2026-08-24T10:00:00Z', ends_at: '2026-08-24T10:30:00Z',
    boundary_note: 'Sandbox action — no real calendar, provider or contact will be used.',
  },
  proposed_actions: [
    { action_type: 'calendar.create', revision: 1, title: 'Review your assessment preparation pack', starts_at: '2026-08-24T10:00:00Z', ends_at: '2026-08-24T10:30:00Z', boundary_note: 'Sandbox action — no real calendar, provider or contact will be used.' },
    { action_type: 'contact_draft.create', revision: 1, title: 'Review your assessment contact draft', starts_at: '', ends_at: '', boundary_note: 'Sandbox draft — it will not be sent without a separate approval.' },
  ],
})

const followedThrough = workflow('follow_through', {
  ...prepared,
  stage: 'follow_through',
  action_result: { case_id: 'case-123', action_type: 'calendar.create', action_revision: 1, channel: 'calendar', payload: { sandbox: 'true', title: 'Review your assessment preparation pack' } },
  action_results: [{ case_id: 'case-123', action_type: 'calendar.create', action_revision: 1, channel: 'calendar', payload: { sandbox: 'true', title: 'Review your assessment preparation pack' } }],
  reminder: { reminder_id: 'reminder-1', action: 'Review the assessment preparation pack', due_at: '2026-08-24T10:00:00Z', status: 'pending' },
  timeline: [
    { event_id: 'event-1', event_type: 'concern.created', details: {}, occurred_at: '2026-08-23T10:00:00Z' },
    { event_id: 'event-2', event_type: 'assessment.pack.prepared', details: {}, occurred_at: '2026-08-23T10:01:00Z' },
    { event_id: 'event-3', event_type: 'approval.granted', details: {}, occurred_at: '2026-08-23T10:02:00Z' },
    { event_id: 'event-4', event_type: 'calendar.action.recorded', details: { sandbox: 'true' }, occurred_at: '2026-08-23T10:02:00Z' },
    { event_id: 'event-5', event_type: 'reminder.scheduled', details: {}, occurred_at: '2026-08-23T10:02:00Z' },
  ],
})

function stubWorkflowFetches() {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => workflow('intake') })
    .mockResolvedValueOnce({ ok: true, json: async () => prepared })
    .mockResolvedValueOnce({ ok: true, json: async () => followedThrough })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('StayLong Continuous Home Path', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('opens with one calm, independent-living task and transparent progress', () => {
    render(<App />)

    expect(document.title).toBe('StayLong | Independent living, coordinated')
    expect(screen.getByRole('link', { name: 'StayLong' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('heading', { name: 'What would make home easier today?' })).toBeVisible()
    expect(screen.getByRole('navigation', { name: 'Continuous Home Path' })).toBeVisible()
    expect(screen.queryByText('If anyone is in immediate danger, call 000.')).not.toBeInTheDocument()
    expect(screen.getByText('If there is immediate danger, call Triple Zero (000).')).toBeVisible()
  })

  it('welcomes a concern that does not match an example', () => {
    render(<App />)

    expect(screen.getByText('Tell StayLong what has become harder at home.')).toBeVisible()
    expect(screen.getByText('Choose an example, or tell us in your own words.')).toBeVisible()
    expect(screen.getByText('No example fits? That’s okay — describe what you noticed below.')).toBeVisible()
  })

  it('turns a chosen example into an editable starting point', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Night-time bathroom' }))

    expect(screen.getByText('You chose: Night-time bathroom')).toBeVisible()
    expect(screen.getByText('We’ve added a starting point below — change the words so they sound like you.')).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' })).toHaveValue(
      'I’m finding it harder to reach the bathroom safely at night. The hallway is dark and there are no rails near the toilet.',
    )
  })

  it('shows an assessment pack and user-controlled action before approval', async () => {
    const user = userEvent.setup()
    const fetchMock = stubWorkflowFetches()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Night-time bathroom' }))
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))
    await screen.findByRole('heading', { name: 'A few details will help prepare your plan' })

    for (const question of questions) {
      await user.type(screen.getByRole('textbox', { name: question.question }), 'A clear answer')
    }
    await user.click(screen.getByRole('button', { name: 'Prepare my plan' }))

    expect(await screen.findByRole('heading', { name: 'Your Home Independence Plan' })).toBeVisible()
    expect(screen.getByText('Arrange a My Aged Care assessment')).toBeVisible()
    expect(screen.getByText('Prepare your assessment notes')).toBeVisible()
    expect(screen.getByText('Confirm home access or permission')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Open My Aged Care' })).toHaveAttribute('href', 'https://www.myagedcare.gov.au/')
    expect(screen.getAllByText('You choose before anything happens.')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Add assessment reminder to calendar' })).toBeEnabled()
    expect(screen.getByText('Contact draft waiting for approval')).toBeVisible()
    expect(screen.getByText('Actions you control')).toBeVisible()
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/v1/workflows', expect.objectContaining({ method: 'POST' }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/v1/workflows/case-123/answers', expect.objectContaining({ method: 'POST' }))
  })

  it('records one approved sandbox action and visible follow-through timeline', async () => {
    const user = userEvent.setup()
    const fetchMock = stubWorkflowFetches()
    render(<App />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), { target: { value: concern } })
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))
    await screen.findByRole('heading', { name: 'A few details will help prepare your plan' })
    for (const question of questions) await user.type(screen.getByRole('textbox', { name: question.question }), 'Answer')
    await user.click(screen.getByRole('button', { name: 'Prepare my plan' }))
    await user.click(await screen.findByRole('button', { name: 'Add assessment reminder to calendar' }))

    expect(await screen.findByText('Reminder added to your plan')).toBeVisible()
    expect(screen.getByText('Contact draft waiting for approval')).toBeVisible()
    const timeline = screen.getByRole('list', { name: 'Plan timeline' })
    expect(within(timeline).getByText('approval.granted')).toBeVisible()
    expect(within(timeline).getByText('reminder.scheduled')).toBeVisible()
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/v1/workflows/case-123/action-decision', expect.objectContaining({ method: 'POST' }))
  })

  it('shows the deterministic 000 route without normal workflow controls', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => workflow('emergency') }))
    const user = userEvent.setup()
    render(<App />)
    await user.type(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), 'My parent is unconscious. Should I wait?')
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))

    expect(await screen.findByRole('heading', { name: 'Call Triple Zero (000) now' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Prepare my plan' })).not.toBeInTheDocument()
  })

  it('lets a person return to their concern while preparing their plan', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => workflow('intake') }))
    render(<App />)

    fireEvent.change(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), { target: { value: concern } })
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))
    await screen.findByRole('heading', { name: 'A few details will help prepare your plan' })
    await user.click(screen.getByRole('button', { name: 'Back to my concern' }))

    expect(screen.getByRole('heading', { name: 'What would make home easier today?' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' })).toHaveValue(concern)
  })

  it('lets a person review assessment details and return to their prepared plan', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => workflow('intake') })
      .mockResolvedValueOnce({ ok: true, json: async () => prepared })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)

    fireEvent.change(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), { target: { value: concern } })
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))
    await screen.findByRole('heading', { name: 'A few details will help prepare your plan' })
    for (const question of questions) await user.type(screen.getByRole('textbox', { name: question.question }), 'Answer')
    await user.click(screen.getByRole('button', { name: 'Prepare my plan' }))
    await screen.findByRole('heading', { name: 'Your Home Independence Plan' })
    await user.click(screen.getByRole('button', { name: 'Back to assessment' }))

    expect(screen.getByRole('heading', { name: 'A few details will help prepare your plan' })).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Return to my plan' }))
    expect(screen.getByRole('heading', { name: 'Your Home Independence Plan' })).toBeVisible()
  })
})

describe('public sandbox mode', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_STAYLONG_API_MODE', 'public-sandbox')
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('uses the public endpoint with credentials without showing internal environment language', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => workflow('intake') })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)
    expect(screen.queryByText('Public sandbox — temporary data, no real bookings or messages.')).not.toBeInTheDocument()
    fireEvent.change(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), { target: { value: concern } })
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))
    expect(fetchMock).toHaveBeenCalledWith('/v1/public/workflows', expect.objectContaining({ credentials: 'include' }))
  })

  it('explains when this browser already has an active sandbox plan', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ detail: 'Public sandbox case limit reached. Please wait for your session to expire.' }),
    }))
    render(<App />)

    fireEvent.change(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), { target: { value: concern } })
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))

    expect(await screen.findByText('This browser already has an active sandbox plan. Open an incognito window or clear this site’s cookies to start a new one.')).toBeVisible()
  })

  it('labels a connected integration only when the workflow reports google_oauth', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ ...prepared, integration_mode: 'google_oauth' }) }))
    render(<App />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), { target: { value: concern } })
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))
    await screen.findByRole('heading', { name: 'Your Home Independence Plan' })
    expect(screen.getByText('Connected Google actions')).toBeVisible()
  })
})
