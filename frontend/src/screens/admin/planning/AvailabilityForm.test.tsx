import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { AvailabilityForm } from './AvailabilityForm';

const mutateAsync = vi.fn();
const toastSuccess = vi.fn();
const toastError = vi.fn();
interface Saved {
  submitted: boolean;
  biannualInterest: string | null;
  monthlyCount: number;
  slotIds: string[];
  updatedAt: string | null;
}
const EMPTY: Saved = {
  submitted: false,
  biannualInterest: null,
  monthlyCount: 0,
  slotIds: [],
  updatedAt: null,
};
let saved = EMPTY;

vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
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
      { id: 's2', label: 'february', month: 2, kind: 'monthly', order: 2 },
      { id: 's3', label: 'spring biannual', month: 4, kind: 'biannual', order: 3 },
    ],
  }),
  useMyAvailability: () => ({ isPending: false, isError: false, data: saved }),
  useSaveAvailability: () => ({ mutateAsync, isPending: false }),
}));

beforeEach(() => {
  mutateAsync.mockReset().mockResolvedValue(undefined);
  toastSuccess.mockReset();
  toastError.mockReset();
  saved = EMPTY;
});

describe('AvailabilityForm', () => {
  it('renders a switch per slot', () => {
    renderWithProviders(<AvailabilityForm year={2027} />);
    expect(screen.getAllByRole('switch')).toHaveLength(3);
    expect(screen.getByRole('switch', { name: 'february' })).not.toBeChecked();
  });

  it('lays monthlies out in two columns and extras below', () => {
    renderWithProviders(<AvailabilityForm year={2027} />);
    const grid = screen.getByTestId('monthly-slots');
    expect(grid.style.gridTemplateRows).toBe('repeat(1, auto)');
    const monthly = within(grid);
    expect(monthly.getByRole('switch', { name: 'january' })).toBeInTheDocument();
    expect(monthly.getByRole('switch', { name: 'february' })).toBeInTheDocument();
    expect(monthly.queryByRole('switch', { name: 'spring biannual' })).not.toBeInTheDocument();
  });

  it('keeps extra slots in the first column, under the monthlies', () => {
    renderWithProviders(<AvailabilityForm year={2027} />);
    const extras = screen.getByTestId('extra-slots');
    expect(extras).toHaveClass('grid-cols-2');
    const toggle = within(extras).getByRole('switch', { name: 'spring biannual' });
    expect(toggle.closest('.col-start-1')).not.toBeNull();
  });

  it('submits selected slot ids, interest and monthly count', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AvailabilityForm year={2027} />);

    await user.click(screen.getByRole('switch', { name: 'january' }));
    await user.click(screen.getByRole('switch', { name: 'spring biannual' }));
    await user.click(screen.getByLabelText('maybe'));
    await user.clear(screen.getByLabelText('how many monthlies will you plan?'));
    await user.type(screen.getByLabelText('how many monthlies will you plan?'), '3');
    await user.click(screen.getByRole('button', { name: 'save availability' }));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        slotIds: ['s1', 's3'],
        biannualInterest: 'maybe',
        monthlyCount: 3,
      });
    });
    expect(toastSuccess).toHaveBeenCalledWith('availability saved 🌱');
  });

  it('leaves the biannual interest unselected and save disabled until one is picked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AvailabilityForm year={2027} />);

    expect(
      screen.getByRole('radiogroup', { name: 'want to plan a biannual?' }),
    ).toBeInTheDocument();
    for (const name of ['yes', 'maybe', 'no']) {
      expect(screen.getByLabelText(name)).not.toBeChecked();
    }
    const save = screen.getByRole('button', { name: 'save availability' });
    expect(save).toBeDisabled();

    await user.click(screen.getByLabelText('no'));
    expect(save).toBeEnabled();
  });

  it.each(['', '2.5', '13', '-1'])('blocks saving when the monthly count is %j', async (bad) => {
    const user = userEvent.setup();
    renderWithProviders(<AvailabilityForm year={2027} />);

    await user.click(screen.getByLabelText('yes'));
    const field = screen.getByLabelText('how many monthlies will you plan?');
    await user.clear(field);
    if (bad) await user.type(field, bad);

    expect(screen.getByText('enter a whole number from 0 to 12')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'save availability' })).toBeDisabled();
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it('prefills a saved answer', () => {
    saved = {
      submitted: true,
      biannualInterest: 'maybe',
      monthlyCount: 4,
      slotIds: ['s2'],
      updatedAt: '2026-11-01T00:00:00Z',
    };
    renderWithProviders(<AvailabilityForm year={2027} />);

    expect(screen.getByRole('switch', { name: 'february' })).toBeChecked();
    expect(screen.getByRole('switch', { name: 'january' })).not.toBeChecked();
    expect(screen.getByLabelText('maybe')).toBeChecked();
    expect(screen.getByLabelText('how many monthlies will you plan?')).toHaveValue(4);
  });

  it('toasts the error and not success when saving fails', async () => {
    mutateAsync.mockRejectedValue(new Error('boom'));
    const user = userEvent.setup();
    renderWithProviders(<AvailabilityForm year={2027} />);

    await user.click(screen.getByLabelText('yes'));
    await user.click(screen.getByRole('button', { name: 'save availability' }));

    await waitFor(() => {
      expect(toastError).toHaveBeenCalledWith("couldn't save availability — try again");
    });
    expect(toastSuccess).not.toHaveBeenCalled();
  });
});
