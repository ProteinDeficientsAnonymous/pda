import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LoadCell, NameCell } from './GridRowCells';

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
    [{ taken: 2, offered: 1 }, '2/1', true],
    [{ taken: 1, offered: 2 }, '1/2', false],
  ])('shows %o as %s, bold %s', (load, text, bold) => {
    render(<LoadCell load={load} style={{}} />);
    expect(screen.getByText(text).classList.contains('font-semibold')).toBe(bold);
  });

  it('shows – without a form', () => {
    render(<LoadCell load={null} style={{}} />);
    expect(screen.getByText('–')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText('no form')).toHaveClass('sr-only');
  });
});
