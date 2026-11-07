import { format } from 'date-fns';

import type { PauseImpactEvent, PauseOutcome, PauseRole } from '@/api/attendancePausePreview';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

const ROLE_LABEL: Record<PauseRole, string> = { rsvp: "rsvp'd", hosting: 'hosting' };
const OUTCOME_LABEL: Record<PauseOutcome, string> = {
  kept: 'kept',
  removed: 'removed',
  drafted: 'moved to draft',
};

interface Props {
  events: PauseImpactEvent[];
  onConfirm: () => void;
  onCancel: () => void;
}

export function AttendancePausePreviewDialog({ events, onConfirm, onCancel }: Props) {
  return (
    <Dialog open onClose={onCancel} title="pause for event rqmt?">
      <p className="text-foreground-secondary mb-3 text-sm">
        here's what happens to their upcoming events once you save
      </p>
      <ul className="flex flex-col gap-2 text-sm">
        {events.map((e) => (
          <li key={`${e.id}:${e.role}`} className="flex flex-col">
            <span className="text-foreground">
              {e.title.toLowerCase()}
              {e.startDatetime ? ` · ${format(e.startDatetime, 'MMM d').toLowerCase()}` : ''}
            </span>
            <span className="text-foreground-tertiary text-xs">
              {ROLE_LABEL[e.role]} · {OUTCOME_LABEL[e.outcome]}
            </span>
          </li>
        ))}
      </ul>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          cancel
        </Button>
        <Button onClick={onConfirm}>pause</Button>
      </div>
    </Dialog>
  );
}
