import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { makeSlot } from '@/test/fixtures';

import { STATE_TEXT } from './gridCell';
import { slotColumns } from './gridLayout';
import { CoverageMark, GridKey } from './GridMarks';
import type { Coverage } from './gridSummary';

describe('CoverageMark', () => {
  it.each<[Coverage, string, string]>([
    [{ kind: 'in' }, '✓', 'in'],
    [{ kind: 'sent' }, '?', 'sent'],
    [{ kind: 'free', count: 2 }, '2', '2 free'],
    [{ kind: 'past' }, '–', 'past'],
  ])('draws %o as %s with words', (coverage, glyph, words) => {
    render(<CoverageMark coverage={coverage} />);
    expect(screen.getByText(glyph)).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText(words)).toHaveClass('sr-only');
  });

  it('calls a draft-only slot not sent yet', () => {
    render(<CoverageMark coverage={{ kind: 'draft' }} />);
    expect(screen.getByText('not sent yet')).toHaveClass('sr-only');
  });

  it('puts a zero count on a dark chip', () => {
    render(<CoverageMark coverage={{ kind: 'free', count: 0 }} />);
    expect(screen.getByText('0')).toHaveClass('bg-plan-ink');
  });
});

describe('GridKey', () => {
  it('labels every tile state in words', () => {
    render(<GridKey columns={[]} />);
    for (const words of Object.values(STATE_TEXT)) {
      expect(screen.getByText(words)).toBeInTheDocument();
    }
    expect(screen.queryByText(/★/)).not.toBeInTheDocument();
  });

  it('spells out the extra slot markers', () => {
    const columns = slotColumns([
      makeSlot({ id: 's1', label: 'january', month: 1, order: 1 }),
      makeSlot({ id: 's2', label: 'june anniversary', month: 6, kind: 'biannual', order: 1 }),
      makeSlot({ id: 's3', label: 'dec holiday', month: 12, kind: 'biannual', order: 2 }),
    ]);
    render(<GridKey columns={columns} />);
    expect(screen.getByText('★ june anniversary · ◆ dec holiday')).toBeInTheDocument();
  });
});
