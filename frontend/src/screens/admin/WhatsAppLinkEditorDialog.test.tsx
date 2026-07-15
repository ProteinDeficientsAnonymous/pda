import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import { describe, expect, it, vi } from 'vitest';

import type { WhatsAppLink } from '@/api/content';

import { WhatsAppLinkEditorDialog } from './WhatsAppLinkEditorDialog';

const mutateAsyncMock = vi.fn();

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/content', () => ({
  useUpdateWhatsAppLink: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderEditor(
  whatsappLink: WhatsAppLink | null = {
    link: 'https://chat.whatsapp.com/abc123',
    updatedAt: '2026-01-01',
  },
) {
  const onClose = vi.fn();
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const utils = render(
    <QueryClientProvider client={qc}>
      <WhatsAppLinkEditorDialog open onClose={onClose} whatsappLink={whatsappLink} />
    </QueryClientProvider>,
  );
  return { ...utils, onClose };
}

describe('WhatsAppLinkEditorDialog', () => {
  it('seeds the input from the loaded link and saves edits', async () => {
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue({
      link: 'https://chat.whatsapp.com/xyz789',
      updatedAt: '2026-01-02',
    });
    const { onClose } = renderEditor({
      link: 'https://chat.whatsapp.com/abc123',
      updatedAt: '2026-01-01',
    });
    const input = screen.getByLabelText('whatsapp link') as HTMLInputElement;
    expect(input.value).toBe('https://chat.whatsapp.com/abc123');
    await userEvent.clear(input);
    await userEvent.type(input, 'https://chat.whatsapp.com/xyz789');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('https://chat.whatsapp.com/xyz789');
    });
    expect(onClose).toHaveBeenCalled();
  });

  it('allows saving an empty link', async () => {
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue({ link: '', updatedAt: '2026-01-02' });
    renderEditor({ link: 'https://chat.whatsapp.com/abc123', updatedAt: '2026-01-01' });
    const input = screen.getByLabelText('whatsapp link') as HTMLInputElement;
    await userEvent.clear(input);
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith('');
    });
  });

  it('shows the FE-rendered error from a structured 422', async () => {
    mutateAsyncMock.mockReset();
    const axiosErr = new AxiosError('Request failed', 'ERR', undefined, undefined, {
      status: 422,
      data: {
        detail: [
          {
            code: 'url.whatsapp_not_recognized',
            field: 'link',
            params: { allowed_hosts: ['chat.whatsapp.com', 'wa.me', 'whats.app'] },
          },
        ],
      },
    } as AxiosResponse);
    mutateAsyncMock.mockRejectedValue(axiosErr);
    renderEditor();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toBeTruthy();
  });
});
