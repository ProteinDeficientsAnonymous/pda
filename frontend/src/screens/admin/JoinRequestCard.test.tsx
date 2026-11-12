import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { JoinRequestStatus, type JoinRequestSummary } from '@/api/join';
import { RejectionReason } from '@/api/rejectionEmail';
import { MembershipStatus } from '@/models/user';
import { makeRequest } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { JoinRequestCard } from './JoinRequestCard';

vi.mock('@/api/users', () => ({
  useUpdateUser: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}));

function renderCard(request: JoinRequestSummary) {
  return renderWithProviders(
    <JoinRequestCard
      request={request}
      busy={false}
      onDecide={vi.fn()}
      onUnreject={vi.fn()}
      onResend={vi.fn()}
    />,
  );
}

describe('JoinRequestCard tentative', () => {
  it('offers no reject and points to archiving from the members screen', () => {
    renderCard(makeRequest({ status: JoinRequestStatus.TENTATIVE, userId: 'u1' }));

    expect(screen.queryByRole('button', { name: 'reject' })).not.toBeInTheDocument();
    expect(screen.getByText(/tentative members can.t be rejected/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'members screen' })).toHaveAttribute(
      'href',
      '/admin/members/u1',
    );
    expect(screen.queryByText(/pause/)).not.toBeInTheDocument();
  });
});

describe('JoinRequestCard decision', () => {
  it('attributes a rejection to whoever last changed the status', () => {
    renderCard(
      makeRequest({
        status: JoinRequestStatus.REJECTED,
        statusChangedAt: '2026-01-02T18:00:00Z',
        statusChangedByName: 'Sam Vettor',
      }),
    );

    expect(screen.getByText(/rejected by sam vettor on jan 2/)).toBeInTheDocument();
  });
});

describe('JoinRequestCard previous archive', () => {
  it('shows when and by whom they were archived', () => {
    renderCard(
      makeRequest({
        previouslyArchived: true,
        previousArchive: {
          archivedAt: '2025-08-14T18:00:00Z',
          archivedByName: 'Robin Admin',
          pausedStatus: null,
        },
      }),
    );

    expect(
      screen.getByText('previously archived on aug 14, 2025 by robin admin'),
    ).toBeInTheDocument();
  });

  it.each([
    [MembershipStatus.GuidelinesPaused, 'while guidelines-paused'],
    [MembershipStatus.AttendancePaused, 'while event rqmt paused'],
  ])('notes the %s pause they were archived under', (pausedStatus, note) => {
    renderCard(
      makeRequest({
        previouslyArchived: true,
        previousArchive: { archivedAt: null, archivedByName: null, pausedStatus },
      }),
    );

    expect(screen.getByText(`previously archived ${note}`)).toBeInTheDocument();
  });

  it('omits the note on a first-time applicant', () => {
    renderCard(makeRequest());

    expect(screen.queryByText(/previously archived on/)).not.toBeInTheDocument();
  });
});

describe('JoinRequestCard previous rejection', () => {
  it('shows who rejected the earlier request, when, and why', () => {
    renderCard(
      makeRequest({
        previouslyRejected: true,
        previousRejection: {
          statusChangedAt: '2025-11-02T18:00:00Z',
          statusChangedByName: 'Sam Vettor',
          rejectionReason: RejectionReason.OTHER,
          rejectionNote: 'asked about leather boots',
        },
      }),
    );

    expect(
      screen.getByText(/previously rejected by sam vettor on nov 2, 2025/),
    ).toBeInTheDocument();
    expect(screen.getByText('reason: asked about leather boots')).toBeInTheDocument();
  });

  it('omits the note on a first-time applicant', () => {
    renderCard(makeRequest());

    expect(screen.queryByText(/previously rejected by/)).not.toBeInTheDocument();
  });
});
