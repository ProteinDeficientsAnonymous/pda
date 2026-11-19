import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { MemberRestoredEmailEditorDialog } from './MemberRestoredEmailEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client');

vi.mock('@/api/memberRestoredEmail', () => ({
  useUpdateMemberRestoredEmail: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe('MemberRestoredEmailEditorDialog', () => {
  it('saves the welcome back email through its own mutation', async () => {
    mutateAsyncMock.mockResolvedValue({ body: 'welcome back', updatedAt: '2026-01-02' });
    renderWithProviders(
      <MemberRestoredEmailEditorDialog
        open
        onClose={vi.fn()}
        template={{ body: 'welcome back', updatedAt: '2026-01-01' }}
      />,
    );
    expect(screen.getByText('${WHATSAPP_LINK}')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('welcome back');
    });
  });
});
