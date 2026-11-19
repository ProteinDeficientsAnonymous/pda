import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { TentativeApprovalMessageEditorDialog } from './TentativeApprovalMessageEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client');

vi.mock('@/api/content', () => ({
  useUpdateTentativeApprovalMessage: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe('TentativeApprovalMessageEditorDialog', () => {
  it('saves the tentative approval message through its own mutation', async () => {
    mutateAsyncMock.mockResolvedValue({ body: 'original', updatedAt: '2026-01-02' });
    renderWithProviders(
      <TentativeApprovalMessageEditorDialog
        open
        onClose={vi.fn()}
        template={{ body: 'original', updatedAt: '2026-01-01' }}
      />,
    );
    expect(screen.getByLabelText('tentative approval message body')).toHaveValue('original');
    expect(screen.getByText('${MAGIC_LINK}')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('original');
    });
  });
});
