import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { AvailabilityAsk } from './AvailabilityAsk';

const openAvailability = vi.fn();
const toastSuccess = vi.fn();
let openedAt: string | null = null;

vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: vi.fn(),
  },
}));

vi.mock('@/api/planning', () => ({
  usePlanningYears: () => ({
    data: [{ id: 'y1', year: 2027, availability_opened_at: openedAt }],
  }),
  useOpenAvailability: () => ({ mutateAsync: openAvailability, isPending: false }),
}));

beforeEach(() => {
  openedAt = null;
  openAvailability.mockReset().mockResolvedValue({});
  toastSuccess.mockReset();
});

describe('AvailabilityAsk', () => {
  it('asks planners only after confirming', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AvailabilityAsk year={2027} />);

    await user.click(screen.getByRole('button', { name: 'ask planners for availability' }));
    expect(
      screen.getByText(/emails every planner asking when they can plan in 2027/),
    ).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'send' }));

    await waitFor(() => {
      expect(openAvailability).toHaveBeenCalledOnce();
    });
    expect(toastSuccess).toHaveBeenCalledWith('planners asked 🌱');
  });

  it('sends nothing when cancelled', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AvailabilityAsk year={2027} />);

    await user.click(screen.getByRole('button', { name: 'ask planners for availability' }));
    await user.click(screen.getByRole('button', { name: 'cancel' }));

    expect(openAvailability).not.toHaveBeenCalled();
  });

  it('shows when planners were asked instead of the button', () => {
    openedAt = '2026-11-16T15:00:00Z';
    renderWithProviders(<AvailabilityAsk year={2027} />);

    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByText(/planners asked for availability on nov 16/)).toBeVisible();
    expect(screen.getByText(/weekly email until 2027 starts/)).toBeVisible();
  });

  it('renders nothing for an unknown year', () => {
    const { container } = renderWithProviders(<AvailabilityAsk year={2031} />);
    expect(container).toBeEmptyDOMElement();
  });
});
