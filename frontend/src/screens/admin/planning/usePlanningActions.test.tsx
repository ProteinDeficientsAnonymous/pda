import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Assignment, PlannerColumn } from '@/api/planning';
import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import type { CellState } from './gridCell';
import { usePlanningActions } from './usePlanningActions';

const propose = vi.fn();
const withdraw = vi.fn();
const toastError = vi.fn();
let pending = { propose: false, withdraw: false, send: false };

vi.mock('sonner', () => ({ toast: { error: (m: string) => void toastError(m) } }));

vi.mock('@/api/planning', () => ({
  usePropose: () => ({ mutateAsync: propose, isPending: pending.propose }),
  useWithdraw: () => ({ mutateAsync: withdraw, isPending: pending.withdraw }),
  useSendProposals: () => ({ mutateAsync: vi.fn(), isPending: pending.send }),
}));

function Harness({ state, status }: { state: CellState; status?: Assignment['status'] }) {
  const { act, busy, confirmElement } = usePlanningActions(2999);
  const slot = makeSlot({ label: 'january' });
  const planner = { userId: 'u1', name: 'ada' } as PlannerColumn;
  const assignment = status ? { id: 'a1', slotId: slot.id, userId: 'u1', status } : undefined;
  return (
    <>
      {confirmElement}
      <button onClick={() => void act(slot, planner, state, assignment)}>go</button>
      <p>{busy ? 'busy' : 'idle'}</p>
    </>
  );
}

async function run(state: CellState, status?: Assignment['status']) {
  renderWithProviders(<Harness state={state} status={status} />);
  await userEvent.click(screen.getByRole('button', { name: 'go' }));
}

const answer = (label: 'withdraw' | 'cancel') =>
  userEvent.click(screen.getByRole('button', { name: label }));

beforeEach(() => {
  vi.resetAllMocks();
  pending = { propose: false, withdraw: false, send: false };
});

describe('usePlanningActions', () => {
  it('proposes a free planner', async () => {
    await run('available');
    expect(propose).toHaveBeenCalledWith({ slotId: 's1', userId: 'u1' });
  });

  it('removes a draft without asking', async () => {
    await run('draft', 'draft');
    expect(screen.queryByRole('button', { name: 'withdraw' })).not.toBeInTheDocument();
    expect(withdraw).toHaveBeenCalledWith('a1');
  });

  it('withdraws only after the coordinator confirms', async () => {
    await run('committed', 'committed');
    expect(screen.getByText('withdraw ada from january?')).toBeInTheDocument();
    await answer('cancel');
    expect(withdraw).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'go' }));
    await answer('withdraw');
    expect(withdraw).toHaveBeenCalledWith('a1');
  });

  it.each([
    ['available', undefined, "couldn't propose that slot — try again"],
    ['draft', 'draft', "couldn't remove that draft — try again"],
    ['committed', 'committed', "couldn't withdraw that slot — try again"],
  ] as const)('toasts when acting on %s fails', async (state, status, message) => {
    propose.mockRejectedValue(new Error('nope'));
    withdraw.mockRejectedValue(new Error('nope'));
    await run(state, status);
    if (state === 'committed') await answer('withdraw');
    expect(toastError).toHaveBeenCalledWith(message);
  });

  it('is idle with nothing in flight', () => {
    renderWithProviders(<Harness state="available" />);
    expect(screen.getByText('idle')).toBeInTheDocument();
  });

  it.each(['propose', 'withdraw', 'send'] as const)('is busy while %s is pending', (key) => {
    pending = { ...pending, [key]: true };
    renderWithProviders(<Harness state="available" />);
    expect(screen.getByText('busy')).toBeInTheDocument();
  });
});
