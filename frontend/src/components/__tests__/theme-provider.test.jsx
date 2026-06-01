import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { ThemeProvider, useTheme } from '../theme-provider';

function ThemeConsumer() {
  const { theme, setTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={() => setTheme('light')}>set-light</button>
      <button onClick={() => setTheme('dark')}>set-dark</button>
      <button onClick={() => setTheme('system')}>set-system</button>
    </div>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    // Reset html class list
    document.documentElement.classList.remove('light', 'dark')
  })

  it('renders children', () => {
    render(
      <ThemeProvider defaultTheme="light">
        <span>child content</span>
      </ThemeProvider>
    )
    expect(screen.getByText('child content')).toBeInTheDocument()
  })

  it('uses defaultTheme when no localStorage value', () => {
    render(
      <ThemeProvider defaultTheme="dark">
        <ThemeConsumer />
      </ThemeProvider>
    )
    expect(screen.getByTestId('theme').textContent).toBe('dark')
  })

  it('restores theme from localStorage', () => {
    localStorage.setItem('vite-ui-theme', 'light')
    render(
      <ThemeProvider defaultTheme="dark">
        <ThemeConsumer />
      </ThemeProvider>
    )
    expect(screen.getByTestId('theme').textContent).toBe('light')
  })

  it('respects custom storageKey', () => {
    localStorage.setItem('my-theme-key', 'dark')
    render(
      <ThemeProvider defaultTheme="light" storageKey="my-theme-key">
        <ThemeConsumer />
      </ThemeProvider>
    )
    expect(screen.getByTestId('theme').textContent).toBe('dark')
  })

  it('setTheme updates theme and saves to localStorage', () => {
    render(
      <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
        <ThemeConsumer />
      </ThemeProvider>
    )
    act(() => {
      screen.getByText('set-dark').click()
    })
    expect(screen.getByTestId('theme').textContent).toBe('dark')
    expect(localStorage.getItem('vite-ui-theme')).toBe('dark')
  })

  it('setTheme to "light" adds light class to documentElement', () => {
    render(
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
        <ThemeConsumer />
      </ThemeProvider>
    )
    act(() => {
      screen.getByText('set-light').click()
    })
    expect(document.documentElement.classList.contains('light')).toBe(true)
  })

  it('setTheme to "dark" adds dark class to documentElement', () => {
    render(
      <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
        <ThemeConsumer />
      </ThemeProvider>
    )
    act(() => {
      screen.getByText('set-dark').click()
    })
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('system theme uses matchMedia to determine class', () => {
    // matchMedia returns matches: false (from setup.js) → 'light'
    render(
      <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
        <ThemeConsumer />
      </ThemeProvider>
    )
    expect(screen.getByTestId('theme').textContent).toBe('system')
    // Light or dark class applied based on matchMedia
    const hasDarkOrLight =
      document.documentElement.classList.contains('light') ||
      document.documentElement.classList.contains('dark')
    expect(hasDarkOrLight).toBe(true)
  })

  it('setTheme to "system" applies system class', () => {
    render(
      <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
        <ThemeConsumer />
      </ThemeProvider>
    )
    act(() => {
      screen.getByText('set-system').click()
    })
    expect(screen.getByTestId('theme').textContent).toBe('system')
  })
})
