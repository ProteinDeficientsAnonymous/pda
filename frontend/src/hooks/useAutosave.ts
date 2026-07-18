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
