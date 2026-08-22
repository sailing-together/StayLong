import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('Calm Companion workspace', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('uses the independent-living product title', () => {
    render(<App />)

    expect(document.title).toBe('StayLong | Independent living, coordinated')
  })

  it('gives the older person one calm next action before showing the composer', async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole('heading', { name: 'What would make home easier today?' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Tell StayLong' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Demo access token')).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'What is getting harder at home?' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Tell StayLong' }))

    expect(screen.getByRole('textbox', { name: 'What is getting harder at home?' })).toBeInTheDocument()
    expect(screen.getAllByText('Nothing is shared, booked, or paid for without your approval.')).toHaveLength(2)
  })

  it('keeps safety routing and the transparent three-stage path visible', () => {
    render(<App />)

    expect(screen.getByText('If anyone is in immediate danger, call 000.')).toBeInTheDocument()
    expect(screen.getByText('Tell us what is happening')).toBeInTheDocument()
    expect(screen.getByText('Prepare for assessment')).toBeInTheDocument()
    expect(screen.getByText('Coordinate approved next steps')).toBeInTheDocument()
  })

  it('creates a case through the authenticated API and renders returned facts', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ case_id: 'case-123', status: 'open' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ([{ concern_id: 'concern-1', case_id: 'case-123', summary: 'Getting to the bathroom at night is difficult.' }]) })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Tell StayLong' }))
    await user.click(screen.getByRole('button', { name: 'Demo settings' }))
    fireEvent.change(screen.getByLabelText('Demo access token'), { target: { value: 'demo-token' } })
    fireEvent.change(screen.getByRole('textbox', { name: 'What is getting harder at home?' }), { target: { value: 'Getting to the bathroom at night is difficult.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Start my plan' }))

    await waitFor(() => expect(screen.getByText('StayLong understood this concern')).toBeInTheDocument())
    expect(screen.getByText('Getting to the bathroom at night is difficult.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review what StayLong understood' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/v1/cases', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({ Authorization: 'Bearer demo-token' }),
      body: JSON.stringify({ summary: 'Getting to the bathroom at night is difficult.' }),
    }))
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/v1/cases/case-123/concerns', {
      headers: { Authorization: 'Bearer demo-token' },
    })
  })
})
