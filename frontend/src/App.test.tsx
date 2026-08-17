import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('family workspace', () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('keeps the case path empty until a real case is created', () => {
    render(<App />)

    expect(screen.getByText('Your case path will appear here.')).toBeInTheDocument()
    expect(screen.queryByText('Active case · open')).not.toBeInTheDocument()
  })

  it('creates a case through the authenticated API and renders returned facts', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ case_id: 'case-123', status: 'open' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ([{ concern_id: 'concern-1', case_id: 'case-123', summary: 'Getting to the bathroom at night is difficult.' }]) })
    vi.stubGlobal('fetch', fetchMock)

    render(<App />)
    fireEvent.change(screen.getByLabelText('Demo access token'), { target: { value: 'demo-token' } })
    fireEvent.change(screen.getByLabelText('What is making home harder?'), { target: { value: 'Getting to the bathroom at night is difficult.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create household case' }))

    await waitFor(() => expect(screen.getByText('Practical concern recorded')).toBeInTheDocument())
    expect(screen.getByText('Getting to the bathroom at night is difficult.', { selector: '.case-details > p' })).toBeInTheDocument()
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
