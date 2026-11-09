import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { JoinRequestStatus, type JoinRequestSummary } from '@/api/join';
import { RejectionReason } from '@/api/rejectionEmail';
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
  it('offers no reject and says to archive or pause instead', () => {
    renderCard(makeRequest({ status: JoinRequestStatus.TENTATIVE }));

    expect(screen.queryByRole('button', { name: 'reject' })).not.toBeInTheDocument();
    expect(screen.getByText(/tentative members can.t be rejected/)).toBeInTheDocument();
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
