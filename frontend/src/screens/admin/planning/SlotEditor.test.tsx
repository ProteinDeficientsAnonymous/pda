import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
      { id: 's1', label: 'january', month: 1, kind: 'monthly', order: 1 },
      { id: 's2', label: 'spring biannual', month: 4, kind: 'biannual', order: 2 },
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

describe('SlotEditor', () => {
  it('renders a row per slot', () => {
    renderWithProviders(<SlotEditor year={2027} />);
    expect(screen.getByLabelText('label for january')).toHaveValue('january');
    expect(screen.getByLabelText('month for spring biannual')).toHaveValue('4');
    expect(screen.getByLabelText('kind for spring biannual')).toHaveValue('biannual');
  });

  it('patches the trimmed label on blur and shows the trimmed value', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    const input = screen.getByLabelText('label for january');
    await user.clear(input);
    await user.type(input, '  jan  ');
    await user.tab();
    expect(updateSlot).toHaveBeenCalledWith({ id: 's1', patch: { label: 'jan' } });
    expect(input).toHaveValue('jan');
  });

  it('does not patch when the label is unchanged', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
    await user.click(screen.getByLabelText('label for january'));
    await user.tab();
    expect(updateSlot).not.toHaveBeenCalled();
  });

  it('reverts an emptied label without patching', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
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
    await user.selectOptions(screen.getByLabelText('month for january'), '3');
    expect(updateSlot).toHaveBeenCalledWith({ id: 's1', patch: { month: 3 } });
    await user.selectOptions(screen.getByLabelText('kind for january'), 'biannual');
    expect(updateSlot).toHaveBeenCalledWith({ id: 's1', patch: { kind: 'biannual' } });
  });

  it('asks to confirm before deleting', async () => {
    const user = userEvent.setup();
    renderWithProviders(<SlotEditor year={2027} />);
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

  it('disables delete while an update is pending', () => {
    updatePending = true;
    renderWithProviders(<SlotEditor year={2027} />);
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
