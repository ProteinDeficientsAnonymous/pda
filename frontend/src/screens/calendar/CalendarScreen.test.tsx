import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useAuthStore } from '@/auth/store';

// react-big-calendar is a heavy component that requires CSS imports and relies
// on browser layout. Stub it so tests focus on CalendarScreen logic.
vi.mock('react-big-calendar', () => ({
  Calendar: ({ isPending }: { isPending?: boolean }) => (
    <div data-testid="rbc-calendar">{isPending ? 'loading…' : 'calendar'}</div>
  ),
  dateFnsLocalizer: vi.fn().mockReturnValue({}),
}));

// Stub calendarLocalizer — it calls dateFnsLocalizer which is mocked above
vi.mock('./calendarLocalizer', () => ({
  makeLocalizer: vi.fn().mockReturnValue({}),
}));

vi.mock('@/api/events', () => ({
  useEvents: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

import { useEvents } from '@/api/events';
import CalendarScreen from './CalendarScreen';

const mockUseEvents = vi.mocked(useEvents);

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderCalendar() {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter>
        <CalendarScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
  vi.clearAllMocks();

  mockUseEvents.mockReturnValue({
    data: [],
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useEvents>);
});

describe('CalendarScreen', () => {
  it('renders the view switcher with view options: month, week, day, list', () => {
    renderCalendar();

    // ViewSwitcher renders a radiogroup labelled "calendar view"
    const radioGroup = screen.getByRole('radiogroup', { name: /calendar view/i });
    expect(radioGroup).toBeInTheDocument();

    // The four view labels
    expect(screen.getByRole('radio', { name: /^month$/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /^week$/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /^day$/i })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /^list$/i })).toBeInTheDocument();
  });

  it('renders the calendar view', () => {
    renderCalendar();

    expect(screen.getByTestId('rbc-calendar')).toBeInTheDocument();
  });

  it('shows loading indicator while events are pending', () => {
    mockUseEvents.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useEvents>);

    renderCalendar();

    expect(screen.getByText(/loading events/i)).toBeInTheDocument();
  });

  it('shows error message and retry button when events fail to load', async () => {
    mockUseEvents.mockReturnValue({
      data: [],
      isPending: false,
      isError: true,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useEvents>);

    renderCalendar();

    expect(screen.getByText(/couldn't load events/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('selecting a different view radio updates the active radio', async () => {
    const user = userEvent.setup();
    renderCalendar();

    const weekRadio = screen.getByRole('radio', { name: /^week$/i });
    await user.click(weekRadio);

    await waitFor(() => {
      expect(weekRadio).toBeChecked();
    });
  });

  it('renders the "go to today" button when the day view is active', async () => {
    const user = userEvent.setup();
    renderCalendar();

    await user.click(screen.getByRole('radio', { name: /^day$/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /go to today/i })).toBeInTheDocument();
    });
  });
});
