import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError, type AxiosResponse } from 'axios';
import { describe, expect, it, vi } from 'vitest';

import type { TentativeApprovalMessage } from '@/api/content';

import TentativeApprovalMessageScreen from './TentativeApprovalMessageScreen';

const mutateAsyncMock = vi.fn();
let queryResult: {
  data: TentativeApprovalMessage | undefined;
  isPending: boolean;
  isError: boolean;
} = { data: { body: 'original', updatedAt: '2026-01-01' }, isPending: false, isError: false };

vi.mock('@/api/client', () => ({
  setAuthBridge: vi.fn(),
  authClient: { post: vi.fn(), get: vi.fn() },
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

vi.mock('@/api/content', () => ({
  useTentativeApprovalMessage: () => queryResult,
  useUpdateTentativeApprovalMessage: () => ({ mutateAsync: mutateAsyncMock, isPending: false }),
}));

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <TentativeApprovalMessageScreen />
    </QueryClientProvider>,
  );
}

describe('TentativeApprovalMessageScreen', () => {
  it('shows a loading state', () => {
    queryResult = { data: undefined, isPending: true, isError: false };
    renderScreen();
    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows an error state', () => {
    queryResult = { data: undefined, isPending: false, isError: true };
    renderScreen();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('seeds the textarea from the loaded message and saves edits', async () => {
    queryResult = {
      data: { body: 'original', updatedAt: '2026-01-01' },
      isPending: false,
      isError: false,
    };
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue({ body: 'updated', updatedAt: '2026-01-02' });
    renderScreen();
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
  });

  it('blocks save when body is empty', async () => {
    queryResult = { data: { body: '', updatedAt: '2026-01-01' }, isPending: false, isError: false };
    mutateAsyncMock.mockReset();
    renderScreen();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('message body is required');
    expect(mutateAsyncMock).not.toHaveBeenCalled();
  });

  it('shows the FE-rendered too-long error from a structured 422', async () => {
    queryResult = {
      data: { body: 'hi', updatedAt: '2026-01-01' },
      isPending: false,
      isError: false,
    };
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
    renderScreen();
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    const alert = await screen.findByRole('alert');
    expect(alert.textContent).toContain('approval message must be at most 4000 characters');
  });
});
