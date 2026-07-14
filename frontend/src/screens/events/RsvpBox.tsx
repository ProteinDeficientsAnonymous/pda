import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { RsvpStatus } from '@/models/event';
import { cn } from '@/utils/cn';

import { RsvpNoteField } from './RsvpNoteField';

type RsvpInputStatus = (typeof RsvpStatus)[keyof typeof RsvpStatus];

const STATUS_LABELS: { status: RsvpInputStatus; label: string }[] = [
  { status: RsvpStatus.Attending, label: "i'm going" },
  { status: RsvpStatus.Maybe, label: 'maybe' },
  { status: RsvpStatus.CantGo, label: "can't go" },
];

interface ConfirmArgs {
  status: RsvpInputStatus;
  note?: string;
  hasPlusOne: boolean;
}

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  initialStatus: RsvpInputStatus;
  initialHasPlusOne: boolean;
  allowPlusOnes: boolean;
  onConfirm: (args: ConfirmArgs) => void;
  onClose: () => void;
}

export function RsvpBox({
  open,
  mode,
  initialStatus,
  initialHasPlusOne,
  allowPlusOnes,
  onConfirm,
  onClose,
}: Props) {
  const [status, setStatus] = useState<RsvpInputStatus>(initialStatus);
  const [note, setNote] = useState('');
  const [hasPlusOne, setHasPlusOne] = useState(initialHasPlusOne);

  const showNote = mode === 'create';
  const showPlusOne = allowPlusOnes && status === RsvpStatus.Attending;

  function confirm() {
    const trimmed = note.trim();
    const args: ConfirmArgs = { status, hasPlusOne };
    if (showNote && trimmed) args.note = trimmed;
    onConfirm(args);
  }

  return (
    <Dialog open={open} onClose={onClose} title="RSVP">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap justify-center gap-2">
          {STATUS_LABELS.map((s) => (
            <button
              key={s.status}
              type="button"
              aria-pressed={status === s.status}
              onClick={() => {
                setStatus(s.status);
              }}
              className={cn(
                'inline-flex h-10 items-center rounded-full px-4 text-sm font-medium',
                status === s.status
                  ? 'bg-brand-600 text-brand-on'
                  : 'border-border-strong text-foreground-secondary border',
              )}
            >
              {s.label}
            </button>
          ))}
        </div>

        {showPlusOne ? (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={hasPlusOne}
              onChange={(e) => {
                setHasPlusOne(e.target.checked);
              }}
            />
            bringing a +1
          </label>
        ) : null}

        {showNote ? <RsvpNoteField value={note} onChange={setNote} /> : null}

        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            cancel
          </Button>
          <Button type="button" onClick={confirm}>
            {mode === 'edit' ? 'save' : 'confirm'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
