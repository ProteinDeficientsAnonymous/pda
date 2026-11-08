import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { MemberPromotionMessageEditorDialog } from './MemberPromotionMessageEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client');

vi.mock('@/api/content', () => ({
  useUpdateMemberPromotionMessage: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe('MemberPromotionMessageEditorDialog', () => {
  it('saves the promotion message through its own mutation', async () => {
    mutateAsyncMock.mockResolvedValue({ body: 'original', updatedAt: '2026-01-02' });
    renderWithProviders(
      <MemberPromotionMessageEditorDialog
        open
        onClose={vi.fn()}
        template={{ body: 'original', updatedAt: '2026-01-01' }}
      />,
    );
    expect(screen.getByLabelText('member promotion message body')).toHaveValue('original');
    expect(screen.getByText('${SENDER_NAME}')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('original');
    });
  });
});
