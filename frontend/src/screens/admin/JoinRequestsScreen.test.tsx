import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as JoinApi from '@/api/join';
import { JoinRequestStatus, type JoinRequestSummary } from '@/api/join';

vi.mock('@/api/join', async (importActual) => {
  const actual = await importActual<typeof JoinApi>();
  return {
    ...actual,
    useJoinRequests: vi.fn(),
    useDecideJoinRequest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
    useUnrejectJoinRequest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
    useResendMagicLink: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  };
});

import { useJoinRequests } from '@/api/join';

import JoinRequestsScreen from './JoinRequestsScreen';

const mockUseJoinRequests = vi.mocked(useJoinRequests);

function makeRequest(overrides: Partial<JoinRequestSummary> = {}): JoinRequestSummary {
  return {
    id: 'jr-1',
    fullName: 'Ada Lovelace',
    phoneNumber: '+15551230001',
    answers: [],
    submittedAt: '2026-01-01T00:00:00Z',
    status: JoinRequestStatus.APPROVED,
    userId: null,
    previouslyArchived: false,
    approvedAt: null,
    approvedByName: null,
    rejectedAt: null,
    rejectedByName: null,
    onboardedAt: null,
    attachedUserOfficialRsvpCount: 0,
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

describe('JoinRequestsScreen', () => {
  it('sorts approved requests by approved date, most recent first', async () => {
    mockResult([
      makeRequest({
        id: 'older',
        fullName: 'Older Approval',
        approvedAt: '2026-01-10T00:00:00Z',
      }),
      makeRequest({
        id: 'newer',
        fullName: 'Newer Approval',
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
    mockResult([makeRequest({ approvedAt: '2026-01-10T00:00:00Z' })]);

    renderScreen();
    await userEvent.click(screen.getByRole('radio', { name: 'approved' }));

    expect(screen.getByText(/sorted newest first/)).toBeInTheDocument();
  });

  it('hides the sort hint when there are no rows', () => {
    mockResult([]);

    renderScreen();

    expect(screen.queryByText(/sorted newest first/)).not.toBeInTheDocument();
  });

  it('notes prior official rsvps when the linked user has them', () => {
    mockResult([
      makeRequest({ status: JoinRequestStatus.PENDING, attachedUserOfficialRsvpCount: 3 }),
    ]);

    renderScreen();

    expect(screen.getByText('rsvp’d to 3 official events')).toBeInTheDocument();
  });

  it('uses the singular noun for a single prior official rsvp', () => {
    mockResult([
      makeRequest({ status: JoinRequestStatus.PENDING, attachedUserOfficialRsvpCount: 1 }),
    ]);

    renderScreen();

    expect(screen.getByText('rsvp’d to 1 official event')).toBeInTheDocument();
  });

  it('omits the note when there are no prior official rsvps', () => {
    mockResult([
      makeRequest({ status: JoinRequestStatus.PENDING, attachedUserOfficialRsvpCount: 0 }),
    ]);

    renderScreen();

    expect(screen.queryByText(/rsvp’d to/)).not.toBeInTheDocument();
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
