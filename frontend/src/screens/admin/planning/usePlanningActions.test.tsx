import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { Assignment, PlannerColumn } from '@/api/planning';
import { setAuthed, setUnauthed } from '@/test/auth';
import { makeSlot, makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import type { CellState } from './gridCell';
import { usePlanningActions } from './usePlanningActions';

const propose = vi.fn();
const withdraw = vi.fn();
const confirmPlanner = vi.fn();
const toastError = vi.fn();
let pending = { propose: false, withdraw: false, confirm: false, send: false };

vi.mock('sonner', () => ({ toast: { error: (m: string) => void toastError(m) } }));

vi.mock('@/api/planning', () => ({
  usePropose: () => ({ mutateAsync: propose, isPending: pending.propose }),
  useWithdraw: () => ({ mutateAsync: withdraw, isPending: pending.withdraw }),
  useConfirmPlanner: () => ({ mutateAsync: confirmPlanner, isPending: pending.confirm }),
  useCommit: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useSendProposals: () => ({ mutateAsync: vi.fn(), isPending: pending.send }),
}));

function Harness({
  state,
  status,
  via = 'act',
}: {
  state: CellState;
  status?: Assignment['status'];
  via?: 'act' | 'tap';
}) {
  const actions = usePlanningActions(2999);
  const { busy, confirmElement } = actions;
  const act = actions[via];
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

async function run(state: CellState, status?: Assignment['status'], via?: 'act' | 'tap') {
  renderWithProviders(<Harness state={state} status={status} via={via} />);
  await userEvent.click(screen.getByRole('button', { name: 'go' }));
}

const answer = (label: 'withdraw' | 'cancel' | 'propose again' | 'put me in') =>
  userEvent.click(screen.getByRole('button', { name: label }));

beforeEach(() => {
  vi.resetAllMocks();
  pending = { propose: false, withdraw: false, confirm: false, send: false };
  setUnauthed();
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

  it.each(['propose', 'withdraw', 'confirm', 'send'] as const)(
    'is busy while %s is pending',
    (key) => {
      pending = { ...pending, [key]: true };
      renderWithProviders(<Harness state="available" />);
      expect(screen.getByText('busy')).toBeInTheDocument();
    },
  );
});

describe('tapping a grid tile', () => {
  const asAda = () => {
    setAuthed(makeUser({ id: 'u1' }));
  };

  it.each([
    ['available', undefined],
    ['draft', 'draft'],
    ['proposed', 'proposed'],
  ] as const)('puts you straight in from your own %s tile', async (state, status) => {
    asAda();
    await run(state, status, 'tap');
    expect(confirmPlanner).toHaveBeenCalledWith({ slotId: 's1', userId: 'u1' });
    expect(propose).not.toHaveBeenCalled();
    expect(withdraw).not.toHaveBeenCalled();
  });

  it('still asks before withdrawing you from your own committed tile', async () => {
    asAda();
    await run('committed', 'committed', 'tap');
    await answer('withdraw');
    expect(withdraw).toHaveBeenCalledWith('a1');
    expect(confirmPlanner).not.toHaveBeenCalled();
  });

  it('asks before putting you in over your own decline', async () => {
    asAda();
    await run('declined', 'declined', 'tap');
    expect(screen.getByText('put yourself in for january? you said no')).toBeInTheDocument();
    await answer('put me in');
    expect(confirmPlanner).toHaveBeenCalledWith({ slotId: 's1', userId: 'u1' });
  });

  it("asks before re-proposing someone else's decline", async () => {
    await run('declined', 'declined', 'tap');
    expect(screen.getByText('propose ada for january again? they said no')).toBeInTheDocument();
    await answer('cancel');
    expect(propose).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'go' }));
    await answer('propose again');
    expect(propose).toHaveBeenCalledWith({ slotId: 's1', userId: 'u1' });
  });

  it("drafts someone else's free tile as before", async () => {
    await run('available', undefined, 'tap');
    expect(propose).toHaveBeenCalledWith({ slotId: 's1', userId: 'u1' });
    expect(confirmPlanner).not.toHaveBeenCalled();
  });

  it('toasts when putting you in fails', async () => {
    asAda();
    confirmPlanner.mockRejectedValue(new Error('nope'));
    await run('available', undefined, 'tap');
    expect(toastError).toHaveBeenCalledWith("couldn't put you in — try again");
  });
});
