// Reconnecting EventSource hook. Mirrors notification_sse_web.dart:
//   - Token is a query param (EventSource can't set Authorization headers).
//   - Exponential backoff 1,2,4,8,16,30s on error (capped at 30s).
//   - Reconnects on every token change so a refresh is picked up naturally.
//
// Usage:
//   useEventSource({
//     url: '/api/notifications/stream/',
//     token: accessToken,
//     events: { notification: () => invalidate(...), connected: () => {} },
//     onStatusChange: setConnected,
//   });

import { useEffect, useRef } from 'react';
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
    let closed = false;

    function connect() {
      const fullUrl = `${API_BASE_URL}${url}?token=${encodeURIComponent(token ?? '')}`;
      es = new EventSource(fullUrl);

      es.addEventListener('open', () => {
        retry = 0;
        onStatusChangeRef.current?.(true);
      });

      for (const [name, handler] of Object.entries(eventsRef.current)) {
        es.addEventListener(name, (ev) => {
          handler(ev as MessageEvent<string>);
        });
      }

      es.addEventListener('error', () => {
        onStatusChangeRef.current?.(false);
        es?.close();
        es = null;
        if (closed) return;
        retry += 1;
        const delay = Math.min(2 ** (retry - 1) * 1000, MAX_BACKOFF_MS);
        reconnectTimer = window.setTimeout(connect, delay);
      });
    }

    connect();

    return () => {
      closed = true;
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      es?.close();
      onStatusChangeRef.current?.(false);
    };
  }, [url, token]);
}
