import { type SyntheticEvent, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { JoinRequestStatus, type JoinRequestSummary, useDecideJoinRequest } from '@/api/join';
import { REJECTION_REASON_LABELS, RejectionReason } from '@/api/rejectionEmail';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { formatPhone } from '@/utils/formatPhone';

const NOTE_MAX_LENGTH = 1000;
const NO_REASON = '';

const REASON_OPTIONS = [
  { value: NO_REASON, label: 'no reason' },
  ...Object.values(RejectionReason).map((value) => ({
    value,
    label: REJECTION_REASON_LABELS[value],
  })),
];

interface Props {
  request: JoinRequestSummary;
  onClose: () => void;
}

export function RejectJoinRequestDialog({ request, onClose }: Props) {
  const decide = useDecideJoinRequest();
  const [reason, setReason] = useState<RejectionReason | typeof NO_REASON>(NO_REASON);
  const [note, setNote] = useState('');
  const [formError, setFormError] = useState<string | null>(null);

  const name = request.fullName || formatPhone(request.phoneNumber);
  const isOther = reason === RejectionReason.OTHER;

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (isOther && !note.trim()) {
      setFormError('write a reason, or pick one from the list');
      return;
    }
    try {
      await decide.mutateAsync({
        id: request.id,
        status: JoinRequestStatus.REJECTED,
        rejectionReason: reason || null,
        rejectionNote: isOther ? note : '',
      });
      onClose();
    } catch (err) {
      setFormError(extractApiErrorOr(err, "couldn't reject the request — try again"));
    }
  }

  return (
    <Dialog open onClose={onClose} title="reject request">
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
        <p className="text-foreground-secondary text-sm">
          reject {name}? you can un-reject them later
        </p>
        <p className="text-muted text-xs">
          {request.email
            ? `they'll get an email at ${request.email.toLowerCase()} — the reason is included if you pick one`
            : "no email on file — they won't be notified"}
        </p>
        <Select
          label="reason"
          labelSuffix="optional"
          options={REASON_OPTIONS}
          value={reason}
          onChange={(e) => {
            setReason(e.target.value as RejectionReason | typeof NO_REASON);
          }}
        />
        {isOther ? (
          <Textarea
            label="reason for the email"
            hint="sent to them as written"
            value={note}
            maxLength={NOTE_MAX_LENGTH}
            onChange={(e) => {
              setNote(e.target.value);
            }}
          />
        ) : null}
        {formError ? (
          <p role="alert" className="text-sm text-red-600">
            {formError}
          </p>
        ) : null}
        <div className="mt-2 flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            cancel
          </Button>
          <Button type="submit" variant="destructive" disabled={decide.isPending}>
            {decide.isPending ? 'rejecting…' : 'reject'}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
