import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { useSendProposals } from '@/api/planning';
import { makeAssignment, makePlanner, makePlanningGrid, makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { SendProposalsBar } from './SendProposalsBar';

const mutateAsync = vi.fn();
const act = vi.fn();
const toastError = vi.fn();
const toastSuccess = vi.fn();

vi.mock('sonner', () => ({
  toast: {
    error: (m: string) => {
      toastError(m);
    },
    success: (m: string) => {
      toastSuccess(m);
    },
  },
}));

beforeEach(() => {
  mutateAsync.mockReset().mockResolvedValue({ planners_notified: 3, proposals_sent: 5 });
  toastError.mockReset();
  toastSuccess.mockReset();
  act.mockReset();
});

const january = makeSlot({ id: 's1', label: 'january', month: 1, order: 1 });
const march = makeSlot({ id: 's3', label: 'march', month: 3, order: 3 });
const ada = makePlanner();
const bo = makePlanner({ userId: 'u2', name: 'bo' });

function draftsGrid(count: number) {
  const assignments = [
    makeAssignment({ id: 'a1', slotId: 's3' }),
    makeAssignment({ id: 'a2', slotId: 's1' }),
    makeAssignment({ id: 'a3', slotId: 's1', userId: 'u2' }),
  ].slice(0, count);
  return makePlanningGrid({ slots: [january, march], planners: [ada, bo], assignments });
}

function renderBar(drafts: number, isPending = false) {
  const send = { mutateAsync, isPending } as unknown as ReturnType<typeof useSendProposals>;
  renderWithProviders(
    <SendProposalsBar grid={draftsGrid(drafts)} send={send} act={act} busy={isPending} />,
  );
}

describe('SendProposalsBar', () => {
  it('is hidden without drafts', () => {
    renderBar(0);
    expect(screen.queryByRole('button', { name: 'send proposals' })).not.toBeInTheDocument();
    expect(screen.queryByText(/not sent yet/)).not.toBeInTheDocument();
  });

  it.each([1, 2])('shows the count of %i unsent drafts', (count) => {
    renderBar(count);
    expect(screen.getByText(`${String(count)} not sent yet`)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'send proposals' })).toBeInTheDocument();
  });

  it('lists the queued drafts by planner in slot order', async () => {
    renderBar(3);
    const toggle = screen.getByRole('button', { name: /3 not sent yet/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    const rows = screen.getAllByRole('listitem').map((li) => li.textContent);
    expect(rows).toEqual(['ada·january✕march✕', 'bo·january✕']);
  });

  async function openDrop() {
    renderBar(1);
    await userEvent.click(screen.getByRole('button', { name: /not sent yet/ }));
    await userEvent.click(screen.getByRole('button', { name: 'drop draft ada for march' }));
    expect(
      screen.getByText("ada won't get a proposal for march — you can draft it again from the grid"),
    ).toBeInTheDocument();
  }

  it('drops a queued draft once confirmed', async () => {
    await openDrop();
    expect(act).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: 'drop draft' }));
    expect(act).toHaveBeenCalledWith(
      march,
      ada,
      'draft',
      makeAssignment({ id: 'a1', slotId: 's3' }),
    );
  });

  it('keeps the draft when the drop is cancelled', async () => {
    await openDrop();
    await userEvent.click(screen.getByRole('button', { name: 'cancel' }));
    expect(act).not.toHaveBeenCalled();
  });

  it('sends the drafts, toasts who was notified and collapses the queue', async () => {
    renderBar(1);
    const toggle = screen.getByRole('button', { name: /not sent yet/ });
    await userEvent.click(toggle);
    await userEvent.click(screen.getByRole('button', { name: 'send proposals' }));
    expect(mutateAsync).toHaveBeenCalled();
    expect(toastSuccess).toHaveBeenCalledWith('sent to 3 planners 🌱');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('toasts when sending fails', async () => {
    mutateAsync.mockRejectedValue(new Error('nope'));
    renderBar(1);
    await userEvent.click(screen.getByRole('button', { name: 'send proposals' }));
    expect(toastError).toHaveBeenCalledWith("couldn't send proposals — try again");
    expect(toastSuccess).not.toHaveBeenCalled();
  });

  it('disables the button while pending', () => {
    renderBar(1, true);
    expect(screen.getByRole('button', { name: 'send proposals' })).toBeDisabled();
  });
});
