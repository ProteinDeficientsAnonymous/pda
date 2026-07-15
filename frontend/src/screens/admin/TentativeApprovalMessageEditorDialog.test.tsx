import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import { describe, expect, it, vi } from 'vitest';

import type { TentativeApprovalMessage } from '@/api/content';

import { TentativeApprovalMessageEditorDialog } from './TentativeApprovalMessageEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/content', () => ({
  useUpdateTentativeApprovalMessage: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderEditor(
  template: TentativeApprovalMessage | null = { body: 'hi', updatedAt: '2026-01-01' },
) {
  const onClose = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = render(
    <QueryClientProvider client={qc}>
      <TentativeApprovalMessageEditorDialog open onClose={onClose} template={template} />
    </QueryClientProvider>,
  );
  return { ...utils, onClose };
}

describe('TentativeApprovalMessageEditorDialog', () => {
  it('seeds the textarea from the loaded message and saves edits', async () => {
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue({ body: 'updated', updatedAt: '2026-01-02' });
    const { onClose } = renderEditor({ body: 'original', updatedAt: '2026-01-01' });
    const textarea = screen.getByLabelText(
      'tentative approval message body',
    ) as HTMLTextAreaElement;
    expect(textarea.value).toBe('original');
    await userEvent.clear(textarea);
    await userEvent.type(textarea, 'updated');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('updated');
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('shows the FE-rendered too-long error from a structured 422', async () => {
    mutateAsyncMock.mockReset();
    const axiosErr = new AxiosError('Request failed', 'ERR', undefined, undefined, {
      status: 422,
      data: {
        detail: [
          {
            code: 'tentative_approval_message.body_too_long',
            field: 'body',
            params: { max_length: 4000 },
          },
        ],
      },
    } as AxiosResponse);
    mutateAsyncMock.mockRejectedValue(axiosErr);
    renderEditor({ body: 'hi', updatedAt: '2026-01-01' });
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('approval message must be at most 4000 characters');
  });

  it('blocks save when body is empty', async () => {
    mutateAsyncMock.mockReset();
    renderEditor({ body: '', updatedAt: '2026-01-01' });
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('message body is required');
    expect(mutateAsyncMock).not.toHaveBeenCalled();
  });
});
