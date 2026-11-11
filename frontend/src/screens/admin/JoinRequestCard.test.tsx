import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { JoinRequestStatus, type JoinRequestSummary } from '@/api/join';
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
