import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { addDays, format } from 'date-fns';
import { useEffect } from 'react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { makeEvent } from '@/test/fixtures';

import CalendarScreen from './CalendarScreen';

// react-big-calendar is a heavy component that requires CSS imports and relies
// on browser layout. Stub it so tests focus on CalendarScreen logic.
vi.mock('react-big-calendar', () => ({
  Calendar: ({
    isPending,
    events,
  }: {
    isPending?: boolean;
    events?: { id: string; title: string }[];
  }) => (
    <div data-testid="rbc-calendar">
      {isPending ? 'loading…' : 'calendar'}
      <ul>
        {(events ?? []).map((e) => (
          <li key={e.id}>{e.title}</li>
        ))}
      </ul>
    </div>
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

const mockUseEvents = vi.mocked(useEvents);

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

let currentSearch = '';

function SearchSpy() {
  const { search } = useLocation();
  useEffect(() => {
    currentSearch = search;
  }, [search]);
  return null;
}

function renderCalendar(initialEntry = '/calendar') {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <CalendarScreen />
        <SearchSpy />
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

  it('restores the navigated-to day on a fresh mount at that URL (e.g. browser back)', async () => {
    const tomorrow = addDays(new Date(), 1);
    const expectedLabel = format(tomorrow, 'EEEE, MMM d').toLowerCase();

    renderCalendar(`/calendar?view=day&date=${format(tomorrow, 'yyyy-MM-dd')}`);

    await waitFor(() => {
      expect(screen.getByText(new RegExp(expectedLabel, 'i'))).toBeInTheDocument();
    });
  });

  it('writes stepped-to date into the url, and a fresh mount there restores it', async () => {
    const user = userEvent.setup();
    const today = new Date();
    const { unmount } = renderCalendar(`/calendar?view=day&date=${format(today, 'yyyy-MM-dd')}`);

    await user.click(screen.getByRole('button', { name: /next day/i }));

    const tomorrow = addDays(today, 1);
    const tomorrowLabel = format(tomorrow, 'EEEE, MMM d').toLowerCase();
    await waitFor(() => {
      expect(screen.getByText(new RegExp(tomorrowLabel, 'i'))).toBeInTheDocument();
    });

    // The step must be persisted to the url, not just to component state — that
    // url is what a browser-back lands on.
    expect(currentSearch).toBe(`?view=day&date=${format(tomorrow, 'yyyy-MM-dd')}`);

    unmount();
    renderCalendar(`/calendar${currentSearch}`);

    await waitFor(() => {
      expect(screen.getByText(new RegExp(tomorrowLabel, 'i'))).toBeInTheDocument();
    });
  });

  it('scrolls the list inside the view box so the toggles stay put', async () => {
    const user = userEvent.setup();
    const { container } = renderCalendar();

    await user.click(screen.getByRole('radio', { name: /^list$/i }));

    await waitFor(() => {
      expect(container.querySelector('main > div.min-h-0.flex-1')).not.toBeNull();
    });
    expect(container.querySelector('.overflow-y-auto')).not.toBeNull();
  });

  it('excludes date-tbd and poll events from the month grid', () => {
    mockUseEvents.mockReturnValue({
      data: [
        makeEvent({ id: 'dated', title: 'dated event' }),
        makeEvent({
          id: 'poll',
          title: 'poll event',
          startDatetime: null,
          datetimeTbd: true,
          hasPoll: true,
        }),
        makeEvent({
          id: 'tbd',
          title: 'plain tbd event',
          startDatetime: null,
          datetimeTbd: true,
        }),
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useEvents>);

    renderCalendar();

    expect(screen.getByText('dated event')).toBeInTheDocument();
    expect(screen.queryByText('poll event')).not.toBeInTheDocument();
    expect(screen.queryByText('plain tbd event')).not.toBeInTheDocument();
  });

  it('surfaces date-tbd and poll events in list view', async () => {
    const user = userEvent.setup();
    mockUseEvents.mockReturnValue({
      data: [
        makeEvent({
          id: 'poll',
          title: 'poll event',
          startDatetime: null,
          datetimeTbd: true,
          hasPoll: true,
        }),
        makeEvent({
          id: 'tbd',
          title: 'plain tbd event',
          startDatetime: null,
          datetimeTbd: true,
        }),
      ],
      isPending: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useEvents>);

    renderCalendar();
    await user.click(screen.getByRole('radio', { name: /^list$/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'poll event' })).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: 'plain tbd event' })).toBeInTheDocument();
  });
});
