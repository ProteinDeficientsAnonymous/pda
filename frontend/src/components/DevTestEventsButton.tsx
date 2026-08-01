import { useState } from 'react';
import { toast } from 'sonner';

import { useCreateDevTestEvents, useDeleteDevTestEvents } from '@/api/devTools';
import { useVersion } from '@/api/version';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';

export function DevTestEventsButton() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const { data: version } = useVersion();
  const [open, setOpen] = useState(false);
  const [count, setCount] = useState(1);
  const createEvents = useCreateDevTestEvents();
  const deleteEvents = useDeleteDevTestEvents();

  if (!isAuthed || version?.environment === 'production') return null;

  async function onCreate() {
    try {
      const result = await createEvents.mutateAsync(count);
      const n = result.events.length;
      toast.success(`created ${String(n)} test event${n === 1 ? '' : 's'} 🌱`);
      setOpen(false);
    } catch {
      toast.error("couldn't create test events — try again");
    }
  }

  async function onCleanup() {
    try {
      await deleteEvents.mutateAsync();
      toast.success('test events cleared 🌱');
    } catch {
      toast.error("couldn't clear test events — try again");
    }
  }

  return (
    <>
      <button
        type="button"
        aria-label="dev test events"
        onClick={() => {
          setOpen(true);
        }}
        style={{
          position: 'fixed',
          left: '1rem',
          top: 'calc(2.5rem + env(safe-area-inset-top))',
          zIndex: 30,
          width: '2.5rem',
          height: '2.5rem',
        }}
        className="flex items-center justify-center rounded-full border border-amber-600 bg-amber-100 text-sm font-semibold text-amber-900 shadow-lg transition-colors hover:bg-amber-200"
      >
        🧪
      </button>
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="dev test events"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <button
            type="button"
            aria-label="close"
            onClick={() => {
              setOpen(false);
            }}
            className="absolute inset-0 cursor-default bg-black/60"
          />
          <div className="bg-surface text-foreground relative w-full max-w-xs rounded-lg p-5 shadow-xl">
            <h2 className="mb-1 text-base font-medium">dev test events</h2>
            <p className="text-muted-foreground mb-4 text-sm">
              creates draft events titled <code>[test] ...</code> — {version?.environment ?? 'local'}{' '}
              only
            </p>
            <label className="mb-4 flex items-center gap-2 text-sm">
              count
              <input
                type="number"
                min={1}
                max={20}
                value={count}
                onChange={(e) => {
                  setCount(Number(e.target.value));
                }}
                className="border-border w-16 rounded-md border px-2 py-1"
              />
            </label>
            <div className="flex flex-col gap-2">
              <Button
                onClick={() => {
                  void onCreate();
                }}
                disabled={createEvents.isPending}
                fullWidth
              >
                {createEvents.isPending ? 'creating...' : 'create'}
              </Button>
              <Button
                variant="secondary"
                onClick={() => {
                  void onCleanup();
                }}
                disabled={deleteEvents.isPending}
                fullWidth
              >
                {deleteEvents.isPending ? 'clearing...' : 'clear all test events'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
