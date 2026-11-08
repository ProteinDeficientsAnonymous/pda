import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { MemberPromotionEmailEditorDialog } from './MemberPromotionEmailEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client');

vi.mock('@/api/content', () => ({
  useUpdateMemberPromotionEmail: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe('MemberPromotionEmailEditorDialog', () => {
  it('saves the promotion email through its own mutation', async () => {
    mutateAsyncMock.mockResolvedValue({ body: 'original', updatedAt: '2026-01-02' });
    renderWithProviders(
      <MemberPromotionEmailEditorDialog
        open
        onClose={vi.fn()}
        template={{ body: 'original', updatedAt: '2026-01-01' }}
      />,
    );
    expect(screen.getByLabelText('member promotion email body')).toHaveValue('original');
    expect(screen.getByText('${WHATSAPP_LINK}')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('original');
    });
  });
});
