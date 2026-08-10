import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { RsvpStatusPicker } from '@/components/ui/RsvpStatusPicker';
import {
  type Event,
  type RsvpInputStatus,
  RsvpServerStatus,
  type RsvpServerStatusValue,
  RsvpStatus,
} from '@/models/event';

import { PaymentConfirmStep } from './PaymentConfirmStep';
import { RsvpCommentField } from './RsvpCommentField';
import { usePaymentGate } from './usePaymentGate';

interface ConfirmArgs {
  status: RsvpServerStatusValue;
  comment?: string;
  hasPlusOne: boolean;
  paidConfirmed?: boolean;
}

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  event: Event;
  initialStatus: RsvpServerStatusValue;
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
  event,
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
  // The picker only ever offers attending/maybe/cant_go — waitlisted isn't a
  // pickable choice, it's what attending resolves to at capacity. Still
  // choosing "attending" while having started out waitlisted resubmits as
  // waitlisted so the backend re-runs capacity rather than treating this as
  // a brand new attending request.
  const initialPickerStatus =
    initialStatus === RsvpServerStatus.Waitlisted ? RsvpStatus.Attending : initialStatus;
  const [pickerStatus, setPickerStatus] = useState<RsvpInputStatus>(initialPickerStatus);
  const [comment, setComment] = useState('');
  const [hasPlusOne, setHasPlusOne] = useState(initialHasPlusOne);
  const [showPayment, setShowPayment] = useState(false);
  const needsPaymentFor = usePaymentGate(event);

  const showComment = allowComment ?? mode === 'create';
  const showPlusOne = allowPlusOnes;
  // Already waitlisted — they're editing their spot in the queue, not joining it.
  const alreadyWaitlisted = initialStatus === RsvpServerStatus.Waitlisted;
  const joiningWaitlist =
    pickerStatus === RsvpStatus.Attending && atCapacity && !alreadyWaitlisted;
  const status: RsvpServerStatusValue =
    pickerStatus === RsvpStatus.Attending && initialStatus === RsvpServerStatus.Waitlisted
      ? RsvpServerStatus.Waitlisted
      : pickerStatus;

  function submit(paidConfirmed: boolean) {
    const trimmed = comment.trim();
    const args: ConfirmArgs = { status, hasPlusOne };
    if (showComment && trimmed) args.comment = trimmed;
    if (paidConfirmed) args.paidConfirmed = true;
    onConfirm(args);
  }

  function confirm() {
    if (needsPaymentFor(pickerStatus)) {
      setShowPayment(true);
      return;
    }
    submit(false);
  }

  return (
    <Dialog open={open} onClose={onClose} title="rsvp">
      {showPayment ? (
        <PaymentConfirmStep
          event={event}
          busy={busy}
          onConfirm={() => {
            submit(true);
          }}
          onBack={() => {
            setShowPayment(false);
          }}
        />
      ) : (
        <div className="flex flex-col gap-4">
          <RsvpStatusPicker
            value={pickerStatus}
            onSelect={setPickerStatus}
            disabled={busy}
            labelFor={(s, defaultLabel) =>
              s === RsvpStatus.Attending && atCapacity && !alreadyWaitlisted
                ? 'join the waitlist'
                : defaultLabel
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
      )}
    </Dialog>
  );
}

function confirmLabel(mode: 'create' | 'edit', joiningWaitlist: boolean): string {
  if (joiningWaitlist) return 'join the waitlist';
  if (mode === 'edit') return 'save';
  return 'confirm';
}
