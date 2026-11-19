import { useEffect, useState } from 'react';

const MAX_TIMEOUT_MS = 2 ** 31 - 1;

export function useRerenderAt(at: Date | null): void {
  const atMs = at?.getTime() ?? null;
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (atMs === null) return;
    // +1 so the re-render lands strictly after `at`, matching isRsvpDeadlinePassed's `<`.
    const delay = atMs - Date.now() + 1;
    if (delay <= 0) return;
    // A clamped timer fires early; the new tick re-runs this effect to wait out the rest.
    const id = window.setTimeout(
      () => {
        setTick((t) => t + 1);
      },
      Math.min(delay, MAX_TIMEOUT_MS),
    );
    return () => {
      window.clearTimeout(id);
    };
  }, [atMs, tick]);
}
