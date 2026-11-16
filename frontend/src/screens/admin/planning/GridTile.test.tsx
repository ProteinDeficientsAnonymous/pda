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

  it('calls onAct on click', async () => {
    const onAct = renderTile();
    await userEvent.click(screen.getByRole('button'));
    expect(onAct).toHaveBeenCalledOnce();
  });
});
