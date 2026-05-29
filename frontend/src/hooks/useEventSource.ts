import { useEffect, useRef } from 'react';

import { refreshAccessToken } from '@/api/client';
import { fetchSseTicket } from '@/api/notifications';
import { API_BASE_URL } from '@/config/env';

type Handler = (event: MessageEvent<string>) => void;

interface Options {
  url: string;
  token: string | null;
  events: Record<string, Handler>;
  onStatusChange?: (connected: boolean) => void;
}

const MAX_BACKOFF_MS = 30_000;

export function useEventSource({ url, token, events, onStatusChange }: Options): void {
  // Keep the latest handlers in a ref so we don't tear down the connection
  // every time the caller passes new function identities.
  const eventsRef = useRef(events);
  const onStatusChangeRef = useRef(onStatusChange);
  useEffect(() => {
    eventsRef.current = events;
    onStatusChangeRef.current = onStatusChange;
  });

  useEffect(() => {
    if (!token) return;

    let es: EventSource | null = null;
    let retry = 0;
    let reconnectTimer: number | null = null;
    // Holder object so async callbacks read the latest value after cleanup mutates it.
    const state = { closed: false };

    function scheduleReconnect() {
      // EventSource can't see the response status, so we can't tell a 401 from
      // a network blip. Try a refresh — if it succeeds the store token changes
      // and React reruns this effect with the fresh token. If it fails (session
      // dead or backend down) fall back to backoff retry so a transient network
      // error still recovers on its own.
      void refreshAccessToken().then((next) => {
        if (state.closed) return;
        if (next && next !== token) return; // outer effect reruns with new token
        retry += 1;
        const delay = Math.min(2 ** (retry - 1) * 1000, MAX_BACKOFF_MS);
        reconnectTimer = window.setTimeout(() => void connect(), delay);
      });
    }

    function attachHandlers(source: EventSource) {
      source.addEventListener('open', () => {
        retry = 0;
        onStatusChangeRef.current?.(true);
      });
      for (const [name, handler] of Object.entries(eventsRef.current)) {
        source.addEventListener(name, (ev) => {
          handler(ev as MessageEvent<string>);
        });
      }
      source.addEventListener('error', () => {
        onStatusChangeRef.current?.(false);
        source.close();
        es = null;
        if (state.closed) return;
        scheduleReconnect();
      });
    }

    async function connect() {
      let ticket: string;
      try {
        // Mint a fresh single-use ticket. If this fails the session may be gone
        // or the backend is down — back off and retry like any other error.
        ticket = await fetchSseTicket();
      } catch {
        if (!state.closed) scheduleReconnect();
        return;
      }
      if (state.closed) return;
      const fullUrl = `${API_BASE_URL}${url}?ticket=${encodeURIComponent(ticket)}`;
      es = new EventSource(fullUrl);
      attachHandlers(es);
    }

    void connect();

    return () => {
      state.closed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      es?.close();
      onStatusChangeRef.current?.(false);
    };
  }, [url, token]);
}
