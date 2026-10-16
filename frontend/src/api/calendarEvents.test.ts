import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { useAuthStore } from '@/auth/store';

import {
  calendarEventKeys,
  calendarRangeParams,
  monthRange,
  prefetchCalendarEvents,
  upcomingRange,
  useCalendarEvents,
} from './calendarEvents';
import { eventKeys } from './events';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn() },
  authClient: { get: vi.fn(), post: vi.fn() },
  setAuthBridge: vi.fn(),
  getCurrentAccessToken: vi.fn(),
}));

const localIso = (y: number, m: number, d: number) => new Date(y, m, d).toISOString();

function wire(id: string, title: string) {
  return { id, title, start_datetime: '2026-03-10T18:00:00Z', end_datetime: null };
}

function buildWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
  return { qc, Wrapper };
}

beforeEach(() => {
  vi.clearAllMocks();
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
});

describe('calendar ranges', () => {
  it('pads a month by a week on each side so week and day views fit', () => {
    expect(calendarRangeParams(monthRange(new Date(2026, 2, 17)))).toEqual({
      start: localIso(2026, 1, 22),
      end: localIso(2026, 3, 8),
      include_imported: false,
    });
  });

  it('starts the upcoming range at the start of yesterday with no end', () => {
    const range = upcomingRange(new Date(2026, 2, 17, 15, 30));

    expect(calendarRangeParams(range)).toEqual({
      start: localIso(2026, 2, 16),
      include_imported: false,
    });
  });

  it('keys each range under the active list key so list invalidations refetch it', () => {
    const key = calendarEventKeys(true, monthRange(new Date(2026, 2, 1)));

    expect(key.slice(0, 3)).toEqual([...eventKeys.list(true)]);
  });
});

describe('useCalendarEvents', () => {
  it('keeps the last month on screen while an earlier one loads', async () => {
    const { Wrapper } = buildWrapper();
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: [wire('e1', 'march potluck')] });
    const { result, rerender } = renderHook(({ range }) => useCalendarEvents(range), {
      wrapper: Wrapper,
      initialProps: { range: monthRange(new Date(2026, 2, 1)) },
    });
    await waitFor(() => expect(result.current.data?.[0]?.title).toBe('march potluck'));

    vi.mocked(apiClient.get).mockReturnValueOnce(new Promise(() => undefined));
    rerender({ range: monthRange(new Date(2026, 1, 1)) });

    expect(result.current.isPlaceholderData).toBe(true);
    expect(result.current.data?.[0]?.title).toBe('march potluck');
    expect(apiClient.get).toHaveBeenLastCalledWith('/api/community/events/', {
      params: calendarRangeParams(monthRange(new Date(2026, 1, 1))),
    });
  });

  it('drops the previous data when the viewer signs out', async () => {
    useAuthStore.setState({ status: 'authed' });
    const { Wrapper } = buildWrapper();
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: [wire('e1', 'members only')] });
    const range = monthRange(new Date(2026, 2, 1));
    const { result } = renderHook(() => useCalendarEvents(range), { wrapper: Wrapper });
    await waitFor(() => expect(result.current.data).toHaveLength(1));

    vi.mocked(apiClient.get).mockReturnValueOnce(new Promise(() => undefined));
    act(() => {
      useAuthStore.setState({ status: 'unauthed' });
    });

    await waitFor(() => expect(result.current.data).toBeUndefined());
    expect(result.current.isPlaceholderData).toBe(false);
  });
});

describe('prefetchCalendarEvents', () => {
  it('fetches with the refreshed token under the authed key', async () => {
    const { qc } = buildWrapper();
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: [wire('e1', 'members only')] });
    const range = monthRange(new Date(2026, 2, 1));

    await prefetchCalendarEvents(qc, range, 'tok-1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/community/events/', {
      params: calendarRangeParams(range),
      headers: { Authorization: 'Bearer tok-1' },
    });
    expect(qc.getQueryData(calendarEventKeys(true, range))).toHaveLength(1);
    expect(qc.getQueryData(calendarEventKeys(false, range))).toBeUndefined();
  });

  it('fetches anonymously under the signed-out key', async () => {
    const { qc } = buildWrapper();
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: [] });
    const range = upcomingRange();

    await prefetchCalendarEvents(qc, range, null);

    expect(apiClient.get).toHaveBeenCalledWith('/api/community/events/', {
      params: calendarRangeParams(range),
    });
    expect(qc.getQueryData(calendarEventKeys(false, range))).toEqual([]);
  });
});
