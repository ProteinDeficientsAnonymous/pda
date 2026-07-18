// Debounced autosave. Mirrors autosave_mixin.dart semantics:
//   2-second debounce, status machine idle → saving → saved (reverts to
//   idle after 2 s) → error. Save is last-write-wins; the hook doesn't
//   track dirty state explicitly because the editor already reports every
//   change.

import { useCallback, useEffect, useRef, useState } from 'react';

export type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface Options {
  /** Milliseconds of inactivity before firing save. Default 2000. */
  delay?: number;
  /** How long the "saved" badge stays visible before fading to idle. */
  savedBadgeMs?: number;
  /** The save function; receives the latest value. */
  onSave: (value: string) => Promise<void>;
}

interface Handle {
  status: AutosaveStatus;
  /** Schedule a save for the given value. Resets the debounce timer. */
  schedule: (value: string) => void;
  /** Cancel any pending save (e.g. on unmount). Automatic via effect cleanup. */
  cancel: () => void;
  /** Cancel any pending debounce and save the given value immediately. */
  flush: (value: string) => Promise<void>;
}

export function useAutosave({ delay = 2000, savedBadgeMs = 2000, onSave }: Options): Handle {
  const [status, setStatus] = useState<AutosaveStatus>('idle');
  const timerRef = useRef<number | null>(null);
  const savedTimerRef = useRef<number | null>(null);
  const onSaveRef = useRef(onSave);

  // Keep the save callback fresh so the hook user can close over new state
  // without forcing a new debounce window.
  useEffect(() => {
    onSaveRef.current = onSave;
  });

  const cancel = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const runSave = useCallback(
    (value: string) => {
      setStatus('saving');
      return onSaveRef.current(value).then(
        () => {
          setStatus('saved');
          if (savedTimerRef.current !== null) window.clearTimeout(savedTimerRef.current);
          savedTimerRef.current = window.setTimeout(() => {
            setStatus('idle');
          }, savedBadgeMs);
        },
        () => {
          setStatus('error');
        },
      );
    },
    [savedBadgeMs],
  );

  const schedule = useCallback(
    (value: string) => {
      cancel();
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        void runSave(value);
      }, delay);
    },
    [cancel, delay, runSave],
  );

  const flush = useCallback(
    (value: string) => {
      cancel();
      return runSave(value);
    },
    [cancel, runSave],
  );

  useEffect(() => {
    return () => {
      cancel();
      if (savedTimerRef.current !== null) window.clearTimeout(savedTimerRef.current);
    };
  }, [cancel]);

  return { status, schedule, cancel, flush };
}
