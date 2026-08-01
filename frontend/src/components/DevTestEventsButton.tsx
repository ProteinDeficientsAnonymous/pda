import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';

import { type DevTestEventOptions, useCreateDevTestEvents } from '@/api/devTools';
import { useVersion } from '@/api/version';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';

import { DevTestEventOverrides } from './DevTestEventOverrides';

const DEFAULT_OPTIONS: DevTestEventOptions = {
  isPast: false,
  isCanceled: false,
  isOfficial: false,
  isClub: false,
  makeMeHost: false,
  price: '',
  venmoLink: '',
  cashappLink: '',
  zelleInfo: '',
  cohostCount: 5,
  invitedCohostCount: 5,
  goingCount: 5,
  maybeCount: 5,
  cantGoCount: 5,
  invitedCount: 5,
  nonMemberGoingCount: 0,
  rsvpEnabled: true,
  visibility: 'public',
  maxAttendees: null,
  allowPlusOnes: false,
};

export function DevTestEventsButton() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const { data: version } = useVersion();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<DevTestEventOptions>(DEFAULT_OPTIONS);
  const createEvents = useCreateDevTestEvents();
  const navigate = useNavigate();

  if (!isAuthed || version?.environment === 'production') return null;

  async function onCreate() {
    try {
      const event = await createEvents.mutateAsync(options);
      toast.success('created 1 test event 🌱');
      setOpen(false);
      void navigate(`/events/${event.slug || event.id}`);
    } catch {
      toast.error("couldn't create test event — try again");
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
          <div className="bg-surface text-foreground relative flex max-h-[85vh] w-full max-w-sm flex-col rounded-lg p-5 shadow-xl">
            <h2 className="mb-1 text-base font-medium">dev test events</h2>
            <p className="text-muted-foreground mb-4 text-sm">
              creates an event — {version?.environment ?? 'local'} only
            </p>

            <DevTestEventOverrides options={options} onChange={setOptions} />

            <div className="mt-4 flex shrink-0 flex-col gap-2">
              <Button
                onClick={() => {
                  void onCreate();
                }}
                disabled={createEvents.isPending}
                fullWidth
              >
                {createEvents.isPending ? 'creating...' : 'create'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
