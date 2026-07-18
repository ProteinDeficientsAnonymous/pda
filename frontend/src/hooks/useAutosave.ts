import { useCallback, useEffect, useRef, useState } from 'react';

export type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface Options {
  delay?: number;
  savedBadgeMs?: number;
  onSave: (value: string) => Promise<void>;
}

interface Handle {
  status: AutosaveStatus;
  schedule: (value: string) => void;
  cancel: () => void;
  flush: (value: string) => Promise<void>;
}

export function useAutosave({ delay = 2000, savedBadgeMs = 2000, onSave }: Options): Handle {
  const [status, setStatus] = useState<AutosaveStatus>('idle');
  const timerRef = useRef<number | null>(null);
  const savedTimerRef = useRef<number | null>(null);
  const onSaveRef = useRef(onSave);
  const inFlightRef = useRef<{ value: string; promise: Promise<void> } | null>(null);
  const pendingValueRef = useRef<string | null>(null);

  useEffect(() => {
    onSaveRef.current = onSave;
  });

  const cancel = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    pendingValueRef.current = null;
  }, []);

  const runSave = useCallback(
    (value: string) => {
      setStatus('saving');
      const promise = onSaveRef.current(value).then(
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
      inFlightRef.current = { value, promise };
      void promise.finally(() => {
        if (inFlightRef.current?.promise === promise) inFlightRef.current = null;
      });
      return promise;
    },
    [savedBadgeMs],
  );

  const schedule = useCallback(
    (value: string) => {
      cancel();
      pendingValueRef.current = value;
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        pendingValueRef.current = null;
        void runSave(value);
      }, delay);
    },
    [cancel, delay, runSave],
  );

  const flush = useCallback(
    (value: string) => {
      if (timerRef.current === null) {
        if (inFlightRef.current?.value === value) return inFlightRef.current.promise;
        return Promise.resolve();
      }
      cancel();
      return runSave(value);
    },
    [cancel, runSave],
  );

  useEffect(() => {
    return () => {
      if (pendingValueRef.current !== null) void flush(pendingValueRef.current);
      if (savedTimerRef.current !== null) window.clearTimeout(savedTimerRef.current);
    };
  }, [flush]);

  return { status, schedule, cancel, flush };
}
