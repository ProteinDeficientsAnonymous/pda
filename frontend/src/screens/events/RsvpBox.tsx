import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import { type RsvpInputStatus, RsvpStatus } from '@/models/event';

import { RsvpCommentField } from './RsvpCommentField';

interface ConfirmArgs {
  status: RsvpInputStatus;
  comment?: string;
  hasPlusOne: boolean;
}

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  initialStatus: RsvpInputStatus;
  initialHasPlusOne: boolean;
  allowPlusOnes: boolean;
  allowComment?: boolean;
  atCapacity?: boolean;
  busy?: boolean;
  onConfirm: (args: ConfirmArgs) => void;
  onRemove?: (() => void) | undefined;
  onClose: () => void;
}

export function RsvpBox({
  open,
  mode,
  initialStatus,
  initialHasPlusOne,
  allowPlusOnes,
  allowComment,
  atCapacity = false,
  busy = false,
  onConfirm,
  onRemove,
  onClose,
}: Props) {
  const [status, setStatus] = useState<RsvpInputStatus>(initialStatus);
  const [comment, setComment] = useState('');
  const [hasPlusOne, setHasPlusOne] = useState(initialHasPlusOne);

  const showComment = allowComment ?? mode === 'create';
  const showPlusOne = allowPlusOnes;
  const joiningWaitlist = status === RsvpStatus.Attending && atCapacity;

  function confirm() {
    const trimmed = comment.trim();
    const args: ConfirmArgs = { status, hasPlusOne };
    if (showComment && trimmed) args.comment = trimmed;
    onConfirm(args);
  }

  return (
    <Dialog open={open} onClose={onClose} title="rsvp">
      <div className="flex flex-col gap-4">
        <RsvpStatusPicker
          value={status}
          onSelect={setStatus}
          disabled={busy}
          labelFor={(s, defaultLabel) =>
            s === RsvpStatus.Attending && atCapacity ? 'join the waitlist' : defaultLabel
          }
        />

        {showPlusOne ? (
          <div className="flex justify-center">
            <Button
              type="button"
              variant={hasPlusOne ? 'primary' : 'secondary'}
              onClick={() => {
                setHasPlusOne(!hasPlusOne);
              }}
              disabled={busy}
            >
              {hasPlusOne ? 'remove +1' : 'add +1'}
            </Button>
          </div>
        ) : null}

        {showComment ? <RsvpCommentField value={comment} onChange={setComment} /> : null}

        <div className="flex items-center justify-between gap-2">
          {mode === 'edit' && onRemove ? (
            <Button type="button" variant="secondary" onClick={onRemove} disabled={busy}>
              remove rsvp
            </Button>
          ) : (
            <span />
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
              cancel
            </Button>
            <Button type="button" onClick={confirm} disabled={busy}>
              {confirmLabel(mode, joiningWaitlist)}
            </Button>
          </div>
        </div>
      </div>
    </Dialog>
  );
}

function confirmLabel(mode: 'create' | 'edit', joiningWaitlist: boolean): string {
  if (joiningWaitlist) return 'join the waitlist';
  if (mode === 'edit') return 'save';
  return 'confirm';
}
