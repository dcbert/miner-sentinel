import { describe, expect, it } from 'vitest';
import { cn } from '../utils';

describe('cn (class name merge helper)', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes (falsy removed)', () => {
    expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz')
  })

  it('deduplicates tailwind classes (last one wins)', () => {
    const result = cn('text-red-500', 'text-blue-500')
    expect(result).toBe('text-blue-500')
  })

  it('returns empty string for no args', () => {
    expect(cn()).toBe('')
  })

  it('handles undefined and null gracefully', () => {
    expect(cn(undefined, null, 'text-sm')).toBe('text-sm')
  })

  it('handles arrays', () => {
    expect(cn(['text-sm', 'font-bold'])).toBe('text-sm font-bold')
  })
})
