import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { refreshAccessToken } from '@/api/client';
import { fetchSseTicket } from '@/api/notifications';

import { useEventSource } from './useEventSource';

vi.mock('@/api/client', () => ({ refreshAccessToken: vi.fn() }));
vi.mock('@/api/notifications', () => ({ fetchSseTicket: vi.fn() }));

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  listeners: Record<string, ((ev: Event) => void)[]> = {};
  close = vi.fn();
  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }
  addEventListener(name: string, fn: (ev: Event) => void) {
    (this.listeners[name] ??= []).push(fn);
  }
  emit(name: string, ev: Event = new Event(name)) {
    for (const fn of this.listeners[name] ?? []) fn(ev);
  }
}

const mockedFetchTicket = vi.mocked(fetchSseTicket);
const mockedRefresh = vi.mocked(refreshAccessToken);
const scope = { eventId: 'evt-1', token: 'rsvp-tok' };

beforeEach(() => {
  vi.useFakeTimers();
  vi.stubGlobal('EventSource', FakeEventSource);
  FakeEventSource.instances = [];
  mockedFetchTicket.mockReset().mockResolvedValue('ticket-1');
  mockedRefresh.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useEventSource', () => {
  it('does not connect without a token or event scope', async () => {
    renderHook(() => useEventSource({ url: '/stream/', token: null, events: {} }));
    await vi.runAllTimersAsync();
    expect(mockedFetchTicket).not.toHaveBeenCalled();
  });

  it('mints a scoped ticket and opens the stream for a logged-out viewer', async () => {
    const onMessage = vi.fn();
    renderHook(() =>
      useEventSource({
        url: '/stream/',
        token: null,
        eventScope: scope,
        events: { event_updated: onMessage },
      }),
    );
    await vi.advanceTimersByTimeAsync(0);

    expect(mockedFetchTicket).toHaveBeenCalledWith(scope);
    const es = FakeEventSource.instances[0]!;
    expect(es.url).toContain('/stream/?ticket=ticket-1');
    es.emit('event_updated');
    expect(onMessage).toHaveBeenCalledOnce();
  });

  it('backs off without a token refresh when a scoped stream errors', async () => {
    renderHook(() =>
      useEventSource({ url: '/stream/', token: null, eventScope: scope, events: {} }),
    );
    await vi.advanceTimersByTimeAsync(0);
    FakeEventSource.instances[0]!.emit('error');

    await vi.advanceTimersByTimeAsync(1000);
    expect(mockedRefresh).not.toHaveBeenCalled();
    expect(mockedFetchTicket).toHaveBeenCalledTimes(2);
  });

  it('refreshes the session then backs off when an authed stream errors', async () => {
    mockedRefresh.mockResolvedValue(null);
    renderHook(() => useEventSource({ url: '/stream/', token: 'jwt', events: {} }));
    await vi.advanceTimersByTimeAsync(0);
    expect(mockedFetchTicket).toHaveBeenCalledWith(undefined);
    FakeEventSource.instances[0]!.emit('error');

    await vi.advanceTimersByTimeAsync(1000);
    expect(mockedRefresh).toHaveBeenCalledOnce();
    expect(mockedFetchTicket).toHaveBeenCalledTimes(2);
  });
});
