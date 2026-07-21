import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import { type RsvpInputStatus } from '@/models/event';

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
  busy?: boolean;
  statuses?: RsvpInputStatus[];
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
  busy = false,
  statuses,
  onConfirm,
  onRemove,
  onClose,
}: Props) {
  const [status, setStatus] = useState<RsvpInputStatus>(initialStatus);
  const [comment, setComment] = useState('');
  const [hasPlusOne, setHasPlusOne] = useState(initialHasPlusOne);

  const showComment = allowComment ?? mode === 'create';
  const showPlusOne = allowPlusOnes;

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
          {...(statuses ? { statuses } : {})}
        />

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

        {showComment ? <RsvpCommentField value={comment} onChange={setComment} /> : null}

        <div className="flex items-center justify-between gap-2">
          {mode === 'edit' && onRemove ? (
            <Button type="button" variant="ghost" onClick={onRemove} disabled={busy}>
              remove rsvp
            </Button>
          ) : (
            <span />
          )}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onClose} disabled={busy}>
              cancel
            </Button>
            <Button type="button" onClick={confirm} disabled={busy}>
              {mode === 'edit' ? 'save' : 'confirm'}
            </Button>
          </div>
        </div>
      </div>
    </Dialog>
  );
}
