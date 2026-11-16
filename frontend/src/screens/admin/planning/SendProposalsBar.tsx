import { useId, useState } from 'react';
import { toast } from 'sonner';

import type { PlanningGrid, useSendProposals } from '@/api/planning';
import { Button } from '@/components/ui/Button';
import { Chevron } from '@/components/ui/Chevron';

import { cellActionLabel, draftCount, draftsByPlanner } from './gridCell';
import { toastOnError } from './toastOnError';
import type { usePlanningActions } from './usePlanningActions';

type Act = ReturnType<typeof usePlanningActions>['act'];

const plural = (n: number, word: string) => `${String(n)} ${word}${n === 1 ? '' : 's'}`;

interface SendProposalsBarProps {
  grid: PlanningGrid;
  send: ReturnType<typeof useSendProposals>;
  act: Act;
  busy: boolean;
}

export function SendProposalsBar({ grid, send, act, busy }: SendProposalsBarProps) {
  const [open, setOpen] = useState(false);
  const listId = useId();
  const drafts = draftCount(grid);
  if (drafts === 0) return null;

  async function sendAll() {
    const sending = send.mutateAsync();
    if (await toastOnError(sending, "couldn't send proposals — try again")) {
      const { planners_notified } = await sending;
      toast.success(`sent to ${plural(planners_notified, 'planner')} 🌱`);
    }
  }

  return (
    <div className="bg-brand-600 text-brand-on rounded-lg p-2">
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          aria-expanded={open}
          aria-controls={listId}
          onClick={() => {
            setOpen((o) => !o);
          }}
          className="hover:bg-brand-700 focus-visible:ring-brand-200 flex h-10 min-w-0 items-center gap-1 rounded-md px-3 text-sm font-medium focus-visible:ring-2 focus-visible:outline-none"
        >
          <span className="truncate">{`${String(drafts)} not sent yet`}</span>
          <Chevron open={open} />
        </button>
        <Button
          disabled={send.isPending}
          onClick={() => void sendAll()}
          className="bg-brand-on text-brand-600 hover:bg-brand-on/90 disabled:bg-brand-on/70 shrink-0"
        >
          send proposals
        </Button>
      </div>
      {open ? (
        <ul id={listId} className="flex flex-col gap-2 px-3 pt-1 pb-2 text-sm">
          {draftsByPlanner(grid).map(({ planner, drafts: queued }) => (
            <li key={planner.userId} className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="font-medium">{planner.name}</span>
              <span aria-hidden="true">·</span>
              {queued.map(({ slot, assignment }) => (
                <button
                  key={assignment.id}
                  type="button"
                  disabled={busy}
                  aria-label={cellActionLabel('draft', planner.name, slot.label)}
                  onClick={() => void act(slot, planner, 'draft', assignment)}
                  className="border-brand-on/40 hover:bg-brand-700 focus-visible:ring-brand-200 inline-flex min-h-8 items-center gap-1 rounded-full border px-2.5 text-xs focus-visible:ring-2 focus-visible:outline-none disabled:opacity-60"
                >
                  {slot.label}
                  <span aria-hidden="true">✕</span>
                </button>
              ))}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
