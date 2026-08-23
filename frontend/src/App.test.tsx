import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

function stubSuccessfulCase() {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({ case_id: 'case-123', status: 'open' }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ([{ concern_id: 'concern-1', case_id: 'case-123', summary: 'Getting to the bathroom at night is difficult.' }]) })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('Calm Companion workspace', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('uses the independent-living product title', () => {
    render(<App />)

    expect(document.title).toBe('StayLong | Independent living, coordinated')
  })

  it('uses the approved StayLong logo in the product header', () => {
    render(<App />)

    expect(screen.getByRole('img', { name: 'StayLong' })).toHaveAttribute(
      'src',
      '/brand/staylong-lockup.svg',
    )
  })

  it('opens directly on one guided task with visible plan progress', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'What would make home easier today?' })).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Continuous Home Path' })).toBeInTheDocument()
    expect(screen.getByText('Step 1 of 4')).toBeInTheDocument()
    expect(screen.getByText('Not started')).toBeInTheDocument()
    expect(screen.getByText('No one invited')).toBeInTheDocument()
  })

  it('lets the person select an example and edit the populated description', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Night-time bathroom' }))

    const description = screen.getByRole('textbox', { name: 'Describe what is becoming difficult' })
    expect(description).toHaveValue(
      'I’m finding it harder to reach the bathroom safely at night. The hallway is dark and there are no rails near the toilet.',
    )
    expect(screen.getByRole('button', { name: 'Night-time bathroom' })).toHaveAttribute('aria-pressed', 'true')

    await user.type(description, ' I would like help preparing the next steps.')
    expect((description as HTMLTextAreaElement).value).toContain('I would like help preparing the next steps.')
  })

  it('keeps safety routing and the transparent four-stage path visible', () => {
    render(<App />)

    expect(screen.getByText('If anyone is in immediate danger, call 000.')).toBeInTheDocument()
    const path = screen.getByRole('navigation', { name: 'Continuous Home Path' })
    expect(within(path).getByText('Tell us what is difficult')).toBeInTheDocument()
    expect(within(path).getByText('Prepare for assessment')).toBeInTheDocument()
    expect(within(path).getByText('Approve next steps')).toBeInTheDocument()
    expect(within(path).getByText('Follow through')).toBeInTheDocument()
  })

  it('creates a case through the authenticated API and renders returned facts', async () => {
    const fetchMock = stubSuccessfulCase()

    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Demo settings' }))
    fireEvent.change(screen.getByLabelText('Demo access token'), { target: { value: 'demo-token' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), { target: { value: 'Getting to the bathroom at night is difficult.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Start my plan' }))

    await waitFor(() => expect(screen.getByText('StayLong understood this concern')).toBeInTheDocument())
    expect(screen.getByText('Getting to the bathroom at night is difficult.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review what StayLong understood' })).toBeInTheDocument()
    expect(screen.getByText('Case status: open')).toBeInTheDocument()
    expect(screen.queryByText('Not started')).not.toBeInTheDocument()
    expect(screen.queryByText('Complete')).not.toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/v1/cases', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({ Authorization: 'Bearer demo-token' }),
      body: JSON.stringify({ summary: 'Getting to the bathroom at night is difficult.' }),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/v1/cases/case-123/concerns', {
      headers: { Authorization: 'Bearer demo-token' },
    })
  })

  it('announces and focuses the result, then lets the person start again with a correction', async () => {
    stubSuccessfulCase()
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Demo settings' }))
    await user.type(screen.getByLabelText('Demo access token'), 'demo-token')
    await user.type(screen.getByRole('textbox', { name: 'Describe what is becoming difficult' }), 'Getting to the bathroom at night is difficult.')
    await user.click(screen.getByRole('button', { name: 'Start my plan' }))

    const result = await screen.findByRole('region', { name: 'StayLong understood this concern' })
    await waitFor(() => expect(result).toHaveFocus())
    expect(screen.getByRole('status')).toHaveTextContent('Your concern is recorded.')

    await user.click(screen.getByRole('button', { name: 'Start again with a correction' }))

    const correctionInput = screen.getByRole('textbox', { name: 'Describe what is becoming difficult' })
    expect(correctionInput).toHaveValue('Getting to the bathroom at night is difficult.')
    expect(correctionInput).toHaveFocus()
    expect(screen.queryByRole('region', { name: 'StayLong understood this concern' })).not.toBeInTheDocument()
  })
})
