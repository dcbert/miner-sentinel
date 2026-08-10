import GlobalTimeRange from '@/components/layout/GlobalTimeRange'
import { TimeRangeProvider } from '@/lib/TimeRangeContext'
import { TIME_RANGE_STORAGE_KEY } from '@/lib/timeRange'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

function renderPicker() {
  return render(
    <TimeRangeProvider>
      <GlobalTimeRange />
    </TimeRangeProvider>,
  )
}

describe('GlobalTimeRange', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
  })

  it('shows default Last 24 hours on the chip', () => {
    renderPicker()
    expect(screen.getByText('Range')).toBeInTheDocument()
    expect(screen.getByText('Last 24 hours')).toBeInTheDocument()
  })

  it('opens presets and selects 7 days', async () => {
    const user = userEvent.setup()
    renderPicker()

    await user.click(screen.getByRole('button', { name: /last 24 hours/i }))
    expect(screen.getByRole('dialog', { name: /select time range/i })).toBeInTheDocument()

    await user.click(screen.getByText('Last 7 days'))

    await waitFor(() => {
      expect(screen.getByText('Last 7 days')).toBeInTheDocument()
    })

    const stored = JSON.parse(localStorage.getItem(TIME_RANGE_STORAGE_KEY))
    expect(stored).toEqual({ mode: 'preset', key: '7d' })
  })

  it('applies a custom range', async () => {
    const user = userEvent.setup()
    renderPicker()

    await user.click(screen.getByRole('button', { name: /last 24 hours/i }))
    await user.click(screen.getByRole('button', { name: /^custom$/i }))

    const from = screen.getByLabelText('From')
    const to = screen.getByLabelText('To')

    fireEvent.change(from, { target: { value: '2026-07-01T00:00' } })
    fireEvent.change(to, { target: { value: '2026-07-08T00:00' } })

    await user.click(screen.getByRole('button', { name: /apply range/i }))

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(TIME_RANGE_STORAGE_KEY))
      expect(stored.mode).toBe('custom')
      expect(stored.from).toBeTruthy()
      expect(stored.to).toBeTruthy()
    })
  })
})
