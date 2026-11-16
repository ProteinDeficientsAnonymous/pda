import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { BiCell, LoadCell, NameCell } from './GridRowCells';

const planner = (extra: object = {}) => ({
  userId: 'u1',
  name: 'ada lovelace',
  isPlanner: true,
  hasEmail: true,
  submitted: true,
  biannualInterest: null,
  monthlyCount: 1,
  availableSlotIds: [],
  ...extra,
});

describe('NameCell', () => {
  it.each([
    [{}, false, false],
    [{ submitted: false }, true, true],
    [{ isPlanner: false }, true, false],
  ])('styles %o as muted %s, italic %s', (extra, muted, italic) => {
    render(<NameCell planner={planner(extra)} style={{}} />);
    const cell = screen.getByTitle('ada lovelace');
    expect(cell.classList.contains('text-muted')).toBe(muted);
    expect(cell.classList.contains('italic')).toBe(italic);
    expect(screen.queryByText('no email')).not.toBeInTheDocument();
  });

  it('marks a planner who left in words', () => {
    render(<NameCell planner={planner({ isPlanner: false })} style={{}} />);
    expect(screen.getByText('(left)')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText('no longer a planner')).toHaveClass('sr-only');
  });

  it('flags a missing email', () => {
    render(<NameCell planner={planner({ hasEmail: false })} style={{}} />);
    expect(screen.getByText('no email')).toHaveClass('sr-only');
  });
});

describe('LoadCell', () => {
  it.each([
    [{ taken: 2, offered: 1 }, '2/1', true, '2 of 1 taken, over'],
    [{ taken: 1, offered: 2 }, '1/2', false, '1 of 2 taken'],
  ])('shows %o as %s, bold %s', (load, text, bold, words) => {
    render(<LoadCell load={load} style={{}} />);
    expect(screen.getByText(text).classList.contains('font-semibold')).toBe(bold);
    expect(screen.getByText(words)).toHaveClass('sr-only');
  });

  it('shows – without a form', () => {
    render(<LoadCell load={null} style={{}} />);
    expect(screen.getByText('–')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText('no form')).toHaveClass('sr-only');
  });
});

describe('BiCell', () => {
  it.each([
    ['yes', 'y', false],
    ['maybe', 'm', false],
    ['no', 'n', true],
  ] as const)('shows %s as %s on phones, muted %s', (interest, short, muted) => {
    const { container } = render(<BiCell interest={interest} style={{}} />);
    expect(screen.getByText(short)).toHaveClass('md:hidden');
    expect(screen.getByText(interest)).toHaveClass('hidden', 'md:inline');
    expect(screen.getByText(`biannual: ${interest}`)).toHaveClass('sr-only');
    expect(container.firstElementChild?.classList.contains('text-muted')).toBe(muted);
  });

  it('shows a muted – without an answer', () => {
    const { container } = render(<BiCell interest={null} style={{}} />);
    expect(screen.getByText('–')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText('biannual: no answer')).toHaveClass('sr-only');
    expect(container.firstElementChild).toHaveClass('text-muted');
  });
});
