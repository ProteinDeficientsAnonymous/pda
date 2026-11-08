import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { WelcomeTemplateEditorDialog } from './WelcomeTemplateEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client');

vi.mock('@/api/content', () => ({
  useUpdateWelcomeTemplate: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

describe('WelcomeTemplateEditorDialog', () => {
  it('saves the welcome template through its own mutation', async () => {
    mutateAsyncMock.mockResolvedValue({ body: 'original', updatedAt: '2026-01-02' });
    renderWithProviders(
      <WelcomeTemplateEditorDialog
        open
        onClose={vi.fn()}
        template={{ body: 'original', updatedAt: '2026-01-01' }}
      />,
    );
    expect(screen.getByLabelText('welcome message body')).toHaveValue('original');
    expect(screen.getByText(/shared with all vetters/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('original');
    });
  });
});
