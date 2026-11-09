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
  it('offers no reject and says to archive or pause instead', () => {
    renderCard(makeRequest({ status: JoinRequestStatus.TENTATIVE }));

    expect(screen.queryByRole('button', { name: 'reject' })).not.toBeInTheDocument();
    expect(screen.getByText(/tentative members can.t be rejected/)).toBeInTheDocument();
  });
});
