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
