import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { AxiosError, type AxiosResponse } from 'axios';
import { WelcomeTemplateEditorDialog } from './WelcomeTemplateEditorDialog';
import type { WelcomeTemplate } from '@/api/content';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/content', () => ({
  useUpdateWelcomeTemplate: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderEditor(template: WelcomeTemplate | null = { body: 'hi', updatedAt: '2026-01-01' }) {
  const onClose = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = render(
    <QueryClientProvider client={qc}>
      <WelcomeTemplateEditorDialog open onClose={onClose} template={template} />
    </QueryClientProvider>,
  );
  return { ...utils, onClose };
}

describe('WelcomeTemplateEditorDialog', () => {
  it('seeds the textarea from the loaded template and saves edits', async () => {
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue({ body: 'updated', updatedAt: '2026-01-02' });
    const { onClose } = renderEditor({ body: 'original', updatedAt: '2026-01-01' });
    const textarea = screen.getByLabelText('welcome message body') as HTMLTextAreaElement;
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
            code: 'welcome_template.body_too_long',
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
    expect(alert.textContent).toContain('welcome message must be at most 4000 characters');
  });

  it('blocks save when body is empty', async () => {
    mutateAsyncMock.mockReset();
    renderEditor({ body: '', updatedAt: '2026-01-01' });
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('welcome message body is required');
    expect(mutateAsyncMock).not.toHaveBeenCalled();
  });
});
