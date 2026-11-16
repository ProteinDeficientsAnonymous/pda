import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { SlotEditor } from './SlotEditor';

const updateSlot = vi.fn();
const deleteSlot = vi.fn();
const createSlot = vi.fn();
const toastError = vi.fn();
let updatePending = false;

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: (m: string) => {
      toastError(m);
    },
  },
}));

vi.mock('@/api/planning', () => ({
  usePlanningSlots: () => ({
    isPending: false,
    isError: false,
    data: [
      makeSlot({ id: 's1', label: 'january', month: 1, order: 1 }),
      makeSlot({ id: 's2', label: 'june anniversary', month: 6, kind: 'biannual', order: 2 }),
    ],
  }),
  useUpdateSlot: () => ({ mutateAsync: updateSlot, isPending: updatePending }),
  useCreateSlot: () => ({ mutateAsync: createSlot, isPending: false }),
  useDeleteSlot: () => ({ mutateAsync: deleteSlot, isPending: false }),
}));

beforeEach(() => {
  updatePending = false;
  toastError.mockReset();
  updateSlot.mockReset().mockResolvedValue(undefined);
  deleteSlot.mockReset().mockResolvedValue(undefined);
  createSlot.mockReset().mockResolvedValue(undefined);
});

async function openRow(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByRole('button', { name: `edit ${label}` }));
}

describe('SlotEditor', () => {
  it('renders collapsed rows with a muted kind and month note for non-monthly slots', () => {
    renderWithProviders(<SlotEditor year={2027} />);
    expect(screen.getByRole('heading', { name: 'slots' })).toBeInTheDocument();
    const list = within(screen.getByRole('list'));
    expect(list.getByText('january')).toBeInTheDocument();
    expect(list.getByText('june anniversary')).toBeInTheDocument();
    expect(list.getByText('biannual · june')).toBeInTheDocument();
    expect(list.queryByText(/monthly ·/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('label for june anniversary')).not.toBeInTheDocument();
  });

  it('reveals the controls when a row is expanded', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    const edit = screen.getByRole('button', { name: 'edit june anniversary' });
    expect(edit).toHaveAttribute('aria-expanded', 'false');
    await user.click(edit);
    expect(edit).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByLabelText('label for june anniversary')).toHaveValue('june anniversary');
    expect(screen.getByLabelText('month for june anniversary')).toHaveValue('6');
    expect(screen.getByLabelText('kind for june anniversary')).toHaveValue('biannual');
  });

  it('collapses the row when edit is clicked again', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    const edit = screen.getByRole('button', { name: 'edit june anniversary' });
    expect(edit).not.toHaveAttribute('aria-controls');
    expect(edit).toHaveTextContent('edit');
    await user.click(edit);
    expect(edit).toHaveAttribute('aria-controls');
    expect(edit).toHaveTextContent('done');
    expect(edit).toHaveAccessibleName('done june anniversary');
    await user.click(edit);
    expect(edit).toHaveAttribute('aria-expanded', 'false');
    expect(edit).not.toHaveAttribute('aria-controls');
    expect(screen.queryByLabelText('label for june anniversary')).not.toBeInTheDocument();
  });

  it('patches the trimmed label on blur and shows the trimmed value', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    const input = screen.getByLabelText('label for january');
    await user.clear(input);
    await user.type(input, '  jan  ');
    await user.tab();
    expect(updateSlot).toHaveBeenCalledWith({ id: 's1', patch: { label: 'jan' } });
    expect(input).toHaveValue('jan');
  });

  it('caps slot labels at the backend limit', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    expect(screen.getByLabelText('label for january')).toHaveAttribute('maxlength', '100');
    expect(screen.getByLabelText('new slot label')).toHaveAttribute('maxlength', '100');
  });

  it('does not patch when the label is unchanged', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    await user.click(screen.getByLabelText('label for january'));
    await user.tab();
    expect(updateSlot).not.toHaveBeenCalled();
  });

  it('reverts an emptied label without patching', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    const input = screen.getByLabelText('label for january');
    await user.clear(input);
    await user.tab();
    expect(updateSlot).not.toHaveBeenCalled();
    expect(input).toHaveValue('january');
  });

  it('reverts the label and toasts when the save fails', async () => {
    updateSlot.mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    const input = screen.getByLabelText('label for january');
    await user.clear(input);
    await user.type(input, 'jan');
    await user.tab();
    await waitFor(() => {
      expect(input).toHaveValue('january');
    });
    expect(toastError).toHaveBeenCalledWith("couldn't save slot — try again");
  });

  it('patches the month and kind when changed', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    await user.selectOptions(screen.getByLabelText('month for january'), '3');
    expect(updateSlot).toHaveBeenCalledWith({ id: 's1', patch: { month: 3 } });
    await user.selectOptions(screen.getByLabelText('kind for january'), 'biannual');
    expect(updateSlot).toHaveBeenCalledWith({ id: 's1', patch: { kind: 'biannual' } });
  });

  it('asks to confirm before deleting', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    await user.click(screen.getByRole('button', { name: 'delete january' }));
    expect(
      screen.getByText('delete this slot? anyone proposed or committed to it is dropped'),
    ).toBeInTheDocument();
    expect(deleteSlot).not.toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'delete' }));
    await waitFor(() => {
      expect(deleteSlot).toHaveBeenCalledWith('s1');
    });
  });

  it('disables delete while an update is pending', async () => {
    const user = userEvent.setup();
    updatePending = true;
    renderWithProviders(<SlotEditor year={2027} />);
    await openRow(user, 'january');
    expect(screen.getByRole('button', { name: 'delete january' })).toBeDisabled();
  });

  it('adds a slot from the add row and clears the label', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    const add = screen.getByRole('button', { name: 'add slot' });
    expect(add).toBeDisabled();
    await user.type(screen.getByLabelText('new slot label'), 'march');
    await user.selectOptions(screen.getByLabelText('new slot month'), '3');
    await user.click(add);
    expect(createSlot).toHaveBeenCalledWith({ label: 'march', month: 3, kind: 'monthly' });
    await waitFor(() => {
      expect(screen.getByLabelText('new slot label')).toHaveValue('');
    });
  });
});
