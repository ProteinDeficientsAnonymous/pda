import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvents } from '@/api/events';
import { setUnauthed } from '@/test/auth';
import { makeEvent } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import EventManagementScreen from './EventManagementScreen';

vi.mock('@/api/events', () => ({
  useEvents: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

const mockUseEvents = vi.mocked(useEvents);

function renderScreen() {
  return renderWithProviders(<EventManagementScreen />);
}

beforeEach(() => {
  setUnauthed();
  vi.clearAllMocks();
});

describe('EventManagementScreen', () => {
  it('badges legacy events as kept off the calendar', async () => {
    mockUseEvents.mockReturnValue({
      data: [
        makeEvent({
          id: 'e1',
          title: 'legacy potluck',
          startDatetime: new Date('2023-07-04T00:00:00Z'),
          isPast: true,
          isLegacy: true,
        }),
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useEvents>);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: /^past$/i }));

    expect(screen.getByText('legacy · not on calendar')).toBeInTheDocument();
  });
});
