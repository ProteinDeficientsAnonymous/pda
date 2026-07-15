import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as JoinApi from '@/api/join';
import { JoinRequestStatus, type JoinRequestSummary } from '@/api/join';

vi.mock('@/api/join', async (importOriginal) => {
  const actual = await importOriginal<typeof JoinApi>();
  return {
    ...actual,
    useJoinRequests: vi.fn(),
    useDecideJoinRequest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
    useUnrejectJoinRequest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
    useResendMagicLink: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  };
});

import { useDecideJoinRequest, useJoinRequests } from '@/api/join';

import JoinRequestsScreen from './JoinRequestsScreen';

const mockUseJoinRequests = vi.mocked(useJoinRequests);

function makeRequest(overrides: Partial<JoinRequestSummary> = {}): JoinRequestSummary {
  return {
    id: 'jr-1',
    fullName: 'Ada Lovelace',
    phoneNumber: '+16505550001',
    email: 'ada@example.com',
    answers: [],
    submittedAt: '2026-01-01T00:00:00Z',
    status: JoinRequestStatus.PENDING,
    userId: null,
    previouslyArchived: false,
    approvedAt: null,
    approvedByName: null,
    rejectedAt: null,
    rejectedByName: null,
    onboardedAt: null,
    rsvpBreakdown: {
      attendedOfficial: 0,
      attendedClub: 0,
      upcomingOfficial: 0,
      upcomingClub: 0,
    },
    rsvpEvents: [],
    ...overrides,
  };
}

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <JoinRequestsScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockResult(data: JoinRequestSummary[]) {
  mockUseJoinRequests.mockReturnValue({
    isPending: false,
    isError: false,
    data,
  } as ReturnType<typeof useJoinRequests>);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('JoinRequestsScreen sort', () => {
  it('sorts approved requests by approved date, most recent first', async () => {
    mockResult([
      makeRequest({
        id: 'older',
        fullName: 'Older Approval',
        status: JoinRequestStatus.APPROVED,
        approvedAt: '2026-01-10T00:00:00Z',
      }),
      makeRequest({
        id: 'newer',
        fullName: 'Newer Approval',
        status: JoinRequestStatus.APPROVED,
        approvedAt: '2026-02-10T00:00:00Z',
      }),
    ]);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: 'approved' }));

    const headings = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent);
    expect(headings).toEqual(['Newer Approval', 'Older Approval']);
  });

  it('shows a discoverable sort hint on the pending tab', () => {
    mockResult([makeRequest({ status: JoinRequestStatus.PENDING })]);

    renderScreen();

    expect(screen.getByText('sorted newest first')).toBeInTheDocument();
  });

  it('shows the sort hint within the approved-tab explainer', async () => {
    mockResult([
      makeRequest({ status: JoinRequestStatus.APPROVED, approvedAt: '2026-01-10T00:00:00Z' }),
    ]);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: 'approved' }));

    expect(screen.getByText(/sorted newest first/)).toBeInTheDocument();
  });

  it('hides the sort hint when there are no rows', () => {
    mockResult([]);

    renderScreen();

    expect(screen.queryByText(/sorted newest first/)).not.toBeInTheDocument();
  });

  it('notes attended and upcoming rsvps split by event type', () => {
    mockResult([
      makeRequest({
        status: JoinRequestStatus.PENDING,
        rsvpBreakdown: {
          attendedOfficial: 3,
          attendedClub: 1,
          upcomingOfficial: 2,
          upcomingClub: 1,
        },
      }),
    ]);

    renderScreen();

    expect(screen.getByText('attended 3 official events')).toBeInTheDocument();
    expect(screen.getByText('attended 1 club event')).toBeInTheDocument();
    expect(screen.getByText("rsvp'd for 2 upcoming official events")).toBeInTheDocument();
    expect(screen.getByText("rsvp'd for 1 upcoming club event")).toBeInTheDocument();
  });

  it('omits buckets whose count is zero', () => {
    mockResult([
      makeRequest({
        status: JoinRequestStatus.PENDING,
        rsvpBreakdown: {
          attendedOfficial: 2,
          attendedClub: 0,
          upcomingOfficial: 0,
          upcomingClub: 0,
        },
      }),
    ]);

    renderScreen();

    expect(screen.getByText('attended 2 official events')).toBeInTheDocument();
    expect(screen.queryByText(/club/)).not.toBeInTheDocument();
    expect(screen.queryByText(/upcoming/)).not.toBeInTheDocument();
  });

  it('omits the note entirely when every bucket is zero', () => {
    mockResult([makeRequest({ status: JoinRequestStatus.PENDING })]);

    renderScreen();

    expect(screen.queryByText(/attended/)).not.toBeInTheDocument();
    expect(screen.queryByText(/rsvp'd for/)).not.toBeInTheDocument();
  });

  it('falls back to submitted date when no decision timestamp exists', async () => {
    mockResult([
      makeRequest({
        id: 'first',
        fullName: 'First Pending',
        status: JoinRequestStatus.PENDING,
        submittedAt: '2026-01-05T00:00:00Z',
      }),
      makeRequest({
        id: 'second',
        fullName: 'Second Pending',
        status: JoinRequestStatus.PENDING,
        submittedAt: '2026-03-05T00:00:00Z',
      }),
    ]);

    renderScreen();

    const list = screen.getByRole('list');
    const headings = within(list)
      .getAllByRole('heading', { level: 2 })
      .map((h) => h.textContent);
    expect(headings).toEqual(['Second Pending', 'First Pending']);
  });
});

describe('JoinRequestsScreen card', () => {
  it('shows the email address next to the phone number', () => {
    mockResult([makeRequest({ fullName: 'Ada Lovelace', email: 'ada@example.com' })]);

    renderScreen();

    expect(screen.getByText(/ada@example\.com/)).toBeInTheDocument();
  });
});

describe('JoinRequestsScreen search', () => {
  it('filters by name', async () => {
    mockResult([
      makeRequest({ id: 'a', fullName: 'Ada Lovelace', email: 'ada@example.com' }),
      makeRequest({ id: 'g', fullName: 'Grace Hopper', email: 'grace@example.com' }),
    ]);

    renderScreen();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/^search$/i), 'grace');

    expect(screen.getByText('Grace Hopper')).toBeInTheDocument();
    expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument();
  });

  it('filters by email', async () => {
    mockResult([
      makeRequest({ id: 'a', fullName: 'Ada Lovelace', email: 'ada@example.com' }),
      makeRequest({ id: 'g', fullName: 'Grace Hopper', email: 'grace@example.com' }),
    ]);

    renderScreen();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/^search$/i), 'grace@');

    expect(screen.getByText('Grace Hopper')).toBeInTheDocument();
    expect(screen.queryByText('Ada Lovelace')).not.toBeInTheDocument();
  });

  it('shows a no-match message when the search matches nothing', async () => {
    mockResult([makeRequest({ fullName: 'Ada Lovelace' })]);

    renderScreen();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/^search$/i), 'zzz');

    expect(screen.getByText(/nothing matches/i)).toBeInTheDocument();
  });
});

describe('JoinRequestsScreen pending actions', () => {
  it('shows approve, tentatively approve, and reject buttons on a pending request', () => {
    mockResult([makeRequest({ status: JoinRequestStatus.PENDING })]);

    renderScreen();

    expect(screen.getByRole('button', { name: 'approve' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'tentatively approve' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'reject' })).toBeInTheDocument();
  });

  it('calls decide with tentative status when tentatively approve is confirmed', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ magicLinkToken: null });
    vi.mocked(useDecideJoinRequest).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useDecideJoinRequest>);
    mockResult([makeRequest({ id: 'jr-pending', status: JoinRequestStatus.PENDING })]);

    renderScreen();
    await userEvent.click(screen.getByRole('button', { name: 'tentatively approve' }));
    const dialog = screen.getByRole('dialog');
    await userEvent.click(within(dialog).getByRole('button', { name: 'tentatively approve' }));

    expect(mutateAsync).toHaveBeenCalledWith({
      id: 'jr-pending',
      status: JoinRequestStatus.TENTATIVE,
    });
  });
});

describe('JoinRequestsScreen tentative section', () => {
  it('shows a manually approve button for tentative requests', async () => {
    mockResult([makeRequest({ status: JoinRequestStatus.TENTATIVE })]);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: 'tentative' }));

    expect(screen.getByRole('button', { name: 'manually approve' })).toBeInTheDocument();
  });

  it('shows rsvp events for a tentative request', async () => {
    mockResult([
      makeRequest({
        status: JoinRequestStatus.TENTATIVE,
        rsvpEvents: [
          { eventId: 'e1', title: 'Potluck', startDatetime: '2026-03-01T18:00:00Z' },
          { eventId: 'e2', title: 'Movie Night', startDatetime: null },
        ],
      }),
    ]);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: 'tentative' }));

    expect(screen.getByText(/Potluck/)).toBeInTheDocument();
    expect(screen.getByText(/Movie Night/)).toBeInTheDocument();
  });

  it('hides the rsvp list entirely when there are no rsvps', async () => {
    mockResult([makeRequest({ status: JoinRequestStatus.TENTATIVE, rsvpEvents: [] })]);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: 'tentative' }));

    expect(screen.queryByText(/rsvp/i)).not.toBeInTheDocument();
  });

  it('calls decide with approved status when manually approve is clicked', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({ magicLinkToken: null });
    vi.mocked(useDecideJoinRequest).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useDecideJoinRequest>);
    mockResult([makeRequest({ id: 'jr-tentative', status: JoinRequestStatus.TENTATIVE })]);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: 'tentative' }));
    await userEvent.click(screen.getByRole('button', { name: 'manually approve' }));
    await userEvent.click(screen.getByRole('button', { name: 'approve' }));

    expect(mutateAsync).toHaveBeenCalledWith({
      id: 'jr-tentative',
      status: JoinRequestStatus.APPROVED,
    });
  });
});
