import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as JoinApi from '@/api/join';
import { JoinRequestStatus } from '@/api/join';
import { RejectionReason } from '@/api/rejectionEmail';
import { makeRequest } from '@/test/fixtures';

import { RejectJoinRequestDialog } from './RejectJoinRequestDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/join', async (importOriginal) => ({
  ...(await importOriginal<typeof JoinApi>()),
  useDecideJoinRequest: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

function renderDialog(overrides: Parameters<typeof makeRequest>[0] = {}) {
  const onClose = vi.fn();
  render(<RejectJoinRequestDialog request={makeRequest(overrides)} onClose={onClose} />);
  return { onClose };
}

describe('RejectJoinRequestDialog', () => {
  beforeEach(() => {
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue({});
  });

  it('rejects with no reason by default', async () => {
    const { onClose } = renderDialog();
    await userEvent.click(screen.getByRole('button', { name: 'reject' }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith({
        id: 'jr-1',
        status: JoinRequestStatus.REJECTED,
        rejectionReason: null,
        rejectionNote: '',
      });
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('sends the picked preset reason', async () => {
    renderDialog();
    await userEvent.selectOptions(screen.getByLabelText(/reason/), RejectionReason.VEGETARIAN);
    await userEvent.click(screen.getByRole('button', { name: 'reject' }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith(
        expect.objectContaining({ rejectionReason: RejectionReason.VEGETARIAN }),
      );
    });
  });

  it('requires a note for other and sends it', async () => {
    renderDialog();
    await userEvent.selectOptions(screen.getByLabelText(/^reason/), RejectionReason.OTHER);
    await userEvent.click(screen.getByRole('button', { name: 'reject' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/write a reason/);
    expect(mutateAsyncMock).not.toHaveBeenCalled();

    await userEvent.type(screen.getByLabelText('reason for the email'), 'we are full');
    await userEvent.click(screen.getByRole('button', { name: 'reject' }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith(
        expect.objectContaining({
          rejectionReason: RejectionReason.OTHER,
          rejectionNote: 'we are full',
        }),
      );
    });
  });

  it('says who gets emailed', () => {
    renderDialog();
    expect(screen.getByText(/they'll get an email at ada@example.com/)).toBeInTheDocument();
  });

  it('says nobody is notified without an email on file', () => {
    renderDialog({ email: '' });
    expect(screen.getByText(/no email on file/)).toBeInTheDocument();
  });
});
