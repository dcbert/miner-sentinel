import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from '../AuthContext';
import api from '../api';

vi.mock('../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

// Helper consumer component
function AuthConsumer() {
  const { isAuthenticated, isLoading, user, login, logout, checkAuth, handleUnauthorized } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <span data-testid="user">{user ? user.username : 'none'}</span>
      <button onClick={() => login({ token: 'tok', user: { username: 'alice' } })}>login</button>
      <button onClick={() => logout()}>logout</button>
      <button onClick={() => checkAuth()}>checkAuth</button>
      <button onClick={() => handleUnauthorized()}>handleUnauthorized</button>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    localStorage.clear()
  })

  it('throws when useAuth is used outside provider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(() => {
      render(<AuthConsumer />)
    }).toThrow('useAuth must be used within an AuthProvider')
    consoleError.mockRestore()
  })

  it('starts with isLoading=true and unauthenticated when no token', async () => {
    // No sessionToken in localStorage — checkAuth returns early without calling api.get
    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    // Initially loading
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })
    expect(screen.getByTestId('auth').textContent).toBe('false')
  })

  it('resolves authenticated when token + valid session', async () => {
    localStorage.setItem('sessionToken', 'valid-token')
    api.get.mockResolvedValueOnce({ data: { authenticated: true, user: { username: 'alice' } } })

    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => {
      expect(screen.getByTestId('auth').textContent).toBe('true')
    })
    expect(screen.getByTestId('user').textContent).toBe('alice')
    expect(screen.getByTestId('loading').textContent).toBe('false')
  })

  it('clears auth when backend returns authenticated=false', async () => {
    localStorage.setItem('sessionToken', 'expired-token')
    api.get.mockResolvedValueOnce({ data: { authenticated: false } })

    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })
    expect(screen.getByTestId('auth').textContent).toBe('false')
    expect(localStorage.getItem('sessionToken')).toBeNull()
  })

  it('clears auth when backend throws (401/network error)', async () => {
    localStorage.setItem('sessionToken', 'stale-token')
    api.get.mockRejectedValueOnce({ response: { status: 401 } })

    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })
    expect(screen.getByTestId('auth').textContent).toBe('false')
    expect(localStorage.getItem('sessionToken')).toBeNull()
  })

  it('login sets authenticated and stores token', async () => {
    api.get.mockRejectedValueOnce(new Error('no token'))
    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))

    await act(async () => {
      screen.getByText('login').click()
    })
    expect(screen.getByTestId('auth').textContent).toBe('true')
    expect(screen.getByTestId('user').textContent).toBe('alice')
    expect(localStorage.getItem('sessionToken')).toBe('tok')
  })

  it('logout clears auth and calls api.post', async () => {
    localStorage.setItem('sessionToken', 'valid-token')
    api.get.mockResolvedValueOnce({ data: { authenticated: true, user: { username: 'alice' } } })
    api.post.mockResolvedValueOnce({})

    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('auth').textContent).toBe('true'))

    await act(async () => {
      screen.getByText('logout').click()
    })
    expect(screen.getByTestId('auth').textContent).toBe('false')
    expect(localStorage.getItem('sessionToken')).toBeNull()
    expect(api.post).toHaveBeenCalledWith('/api/auth/logout/')
  })

  it('logout clears auth even when api.post throws', async () => {
    localStorage.setItem('sessionToken', 'valid-token')
    api.get.mockResolvedValueOnce({ data: { authenticated: true, user: { username: 'alice' } } })
    api.post.mockRejectedValueOnce(new Error('network error'))

    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('auth').textContent).toBe('true'))

    await act(async () => {
      screen.getByText('logout').click()
    })
    expect(screen.getByTestId('auth').textContent).toBe('false')
    expect(localStorage.getItem('sessionToken')).toBeNull()
  })

  it('handleUnauthorized clears auth state', async () => {
    localStorage.setItem('sessionToken', 'valid-token')
    api.get.mockResolvedValueOnce({ data: { authenticated: true, user: { username: 'alice' } } })

    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('auth').textContent).toBe('true'))

    act(() => {
      screen.getByText('handleUnauthorized').click()
    })
    expect(screen.getByTestId('auth').textContent).toBe('false')
    expect(localStorage.getItem('sessionToken')).toBeNull()
  })

  it('checkAuth returns false when no sessionToken', async () => {
    render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
    // Second checkAuth with no token
    await act(async () => {
      screen.getByText('checkAuth').click()
    })
    expect(screen.getByTestId('auth').textContent).toBe('false')
  })

  it('exposes window.__authLogout on mount and removes on unmount', async () => {
    api.get.mockRejectedValueOnce(new Error('no token'))
    const { unmount } = render(<AuthProvider><AuthConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('loading').textContent).toBe('false'))
    expect(typeof window.__authLogout).toBe('function')
    unmount()
    expect(window.__authLogout).toBeUndefined()
  })
})
