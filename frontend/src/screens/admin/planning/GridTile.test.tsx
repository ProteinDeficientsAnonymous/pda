import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { type CellState, STATE_TEXT } from './gridCell';
import { GridTile } from './GridTile';

const STATES = Object.keys(STATE_TEXT) as CellState[];

function renderTile(overrides: Partial<Parameters<typeof GridTile>[0]> = {}) {
  const onAct = vi.fn();
  render(
    <GridTile
      state="committed"
      plannerName="ada"
      slotLabel="january"
      isPlanner
      disabled={false}
      onAct={onAct}
      {...overrides}
    />,
  );
  return onAct;
}

describe('GridTile', () => {
  it.each(STATES)('describes the %s state in words', (state) => {
    renderTile({ state });
    expect(screen.getByRole('button')).toHaveAccessibleDescription(STATE_TEXT[state]);
  });

  it.each([
    ['committed', '✓', 'rounded-[3px]'],
    ['proposed', '?', 'rounded-full'],
    ['no_answer', '!', 'rounded-full'],
    ['draft', '', 'rounded-[3px]'],
    ['declined', '✕', 'rounded-[3px]'],
    ['available', '', 'rounded-[3px]'],
    ['blank', '', 'rounded-[3px]'],
  ] as const)('draws %s as glyph "%s" on a %s tile', (state, glyph, shape) => {
    renderTile({ state });
    const tile = screen.getByRole('button').querySelector('[aria-hidden="true"]');
    expect(tile?.textContent).toBe(glyph);
    expect(tile).toHaveClass(shape);
    expect(tile?.querySelector('.rounded-full') !== null).toBe(state === 'available');
  });

  it('names a draft tile by its remove action', () => {
    renderTile({ state: 'draft' });
    expect(screen.getByRole('button', { name: 'remove draft ada for january' })).toBeEnabled();
  });

  it('disables a blank tile for someone who is no longer a planner', () => {
    renderTile({ state: 'blank', isPlanner: false });
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription('not free · no longer a planner');
  });

  it('keeps a committed tile enabled for a non-planner so it can be withdrawn', () => {
    renderTile({ state: 'committed', isPlanner: false });
    expect(screen.getByRole('button')).toBeEnabled();
  });

  it('disables the tile when disabled', () => {
    renderTile({ disabled: true });
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('fits the fixed grid cell footprint and lifts its focus ring over neighbours', () => {
    renderTile();
    expect(screen.getByRole('button')).toHaveClass(
      'h-[var(--pg-row)]',
      'w-[var(--pg-col)]',
      'relative',
      'focus-visible:z-10',
    );
  });

  it('calls onAct on click', async () => {
    const onAct = renderTile();
    await userEvent.click(screen.getByRole('button'));
    expect(onAct).toHaveBeenCalledOnce();
  });
});
