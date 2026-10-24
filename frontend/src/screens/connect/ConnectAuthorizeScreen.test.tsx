import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import ConnectAuthorizeScreen from './ConnectAuthorizeScreen';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);
const REQUEST_ID = '3f2b8c1e-5a4d-4e6f-9b7a-1c2d3e4f5a6b';
const assign = vi.fn();
const originalLocation = window.location;

const REQUEST = {
  client_name: 'claude',
  redirect_host: 'claude.ai',
  expires_at: '2026-10-01T12:10:00Z',
};

function httpError(status: number) {
  return Object.assign(new Error('request failed'), {
    isAxiosError: true,
    response: { status, data: { detail: [] } },
  });
}

function renderScreen(url = `/connect/authorize?request=${REQUEST_ID}`) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <ConnectAuthorizeScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { assign },
  });
});

afterEach(() => {
  Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
  Object.defineProperty(window, 'top', { configurable: true, value: window });
});

describe('ConnectAuthorizeScreen', () => {
  it('shows the app name and redirect host', async () => {
    mockedGet.mockResolvedValueOnce({ data: REQUEST });
    renderScreen();
    expect(
      await screen.findByRole('heading', { name: 'connect claude to pda' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/claude wants to act as you in pda\./)).toBeInTheDocument();
    expect(screen.getByText("after you allow, you'll be sent to claude.ai")).toBeInTheDocument();
    expect(mockedGet).toHaveBeenCalledWith(`/api/connect/requests/${REQUEST_ID}/`);
  });

  it('allow posts approve and navigates to redirect_url', async () => {
    mockedGet.mockResolvedValueOnce({ data: REQUEST });
    mockedPost.mockResolvedValueOnce({ data: { redirect_url: 'https://claude.ai/cb?code=abc' } });
    renderScreen();
    await userEvent.click(await screen.findByRole('button', { name: 'allow' }));
    await waitFor(() => {
      expect(assign).toHaveBeenCalledExactlyOnceWith('https://claude.ai/cb?code=abc');
    });
    expect(mockedPost).toHaveBeenCalledWith(`/api/connect/requests/${REQUEST_ID}/approve/`);
  });

  it('deny posts deny and navigates', async () => {
    mockedGet.mockResolvedValueOnce({ data: REQUEST });
    mockedPost.mockResolvedValueOnce({
      data: { redirect_url: 'https://claude.ai/cb?error=access_denied' },
    });
    renderScreen();
    await userEvent.click(await screen.findByRole('button', { name: 'deny' }));
    await waitFor(() => {
      expect(assign).toHaveBeenCalledExactlyOnceWith('https://claude.ai/cb?error=access_denied');
    });
    expect(mockedPost).toHaveBeenCalledWith(`/api/connect/requests/${REQUEST_ID}/deny/`);
  });

  it('does not navigate to an unsafe or mismatched redirect_url', async () => {
    mockedGet.mockResolvedValueOnce({ data: REQUEST });
    mockedPost.mockResolvedValueOnce({ data: { redirect_url: 'javascript:alert(1)' } });
    renderScreen();
    await userEvent.click(await screen.findByRole('button', { name: 'allow' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      "this app's return address isn't allowed",
    );
    expect(assign).not.toHaveBeenCalled();
  });

  it('disables both buttons while a decision is in flight', async () => {
    mockedGet.mockResolvedValueOnce({ data: REQUEST });
    mockedPost.mockReturnValueOnce(new Promise(() => {}));
    renderScreen();
    await userEvent.click(await screen.findByRole('button', { name: 'allow' }));
    expect(screen.getByRole('button', { name: 'allow' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'deny' })).toBeDisabled();
    expect(mockedPost).toHaveBeenCalledTimes(1);
  });

  it.each([
    [410, 'this request expired. go back to your ai app and try connecting again.'],
    [409, 'this request was already used.'],
    [404, "this connection request doesn't exist."],
  ])('shows the %i message when loading the request fails', async (status, message) => {
    mockedGet.mockRejectedValueOnce(httpError(status));
    renderScreen();
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.queryByRole('button', { name: 'allow' })).not.toBeInTheDocument();
  });

  it('shows the expired message when approving a request that just expired', async () => {
    mockedGet.mockResolvedValueOnce({ data: REQUEST });
    mockedPost.mockRejectedValueOnce(httpError(410));
    renderScreen();
    await userEvent.click(await screen.findByRole('button', { name: 'allow' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('this request expired.');
    expect(assign).not.toHaveBeenCalled();
  });

  it('shows not found without a request id', () => {
    renderScreen('/connect/authorize');
    expect(screen.getByRole('alert')).toHaveTextContent("this connection request doesn't exist.");
    expect(mockedGet).not.toHaveBeenCalled();
  });

  it.each(['../apps', 'r1', 'abc/def', '3f2b8c1e-5a4d-4e6f-9b7a-1c2d3e4f5a6b/../x'])(
    'shows not found and makes no request for non-uuid id %s',
    (id) => {
      renderScreen(`/connect/authorize?request=${encodeURIComponent(id)}`);
      expect(screen.getByRole('alert')).toHaveTextContent("this connection request doesn't exist.");
      expect(mockedGet).not.toHaveBeenCalled();
      expect(mockedPost).not.toHaveBeenCalled();
    },
  );

  it('hides allow and deny when framed in another page', () => {
    Object.defineProperty(window, 'top', { configurable: true, value: {} });
    renderScreen();
    expect(screen.getByRole('alert')).toHaveTextContent(
      'for your security, open this page directly in your browser',
    );
    expect(screen.queryByRole('button', { name: 'allow' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'deny' })).not.toBeInTheDocument();
    expect(mockedGet).not.toHaveBeenCalled();
  });
});
