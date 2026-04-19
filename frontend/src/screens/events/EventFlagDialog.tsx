// Member-facing flag dialog. Sends POST /api/community/events/{id}/flag/
// with a required reason; surfaces the backend's 409 (already flagged) as a
// friendly toast. Max length mirrors the backend BIO field limit (500).

import { useState } from 'react';
import { toast } from 'sonner';
import { FlagEventError, useFlagEvent } from '@/api/eventFlags';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { Textarea } from '@/components/ui/Textarea';

const REASON_MAX = 500;

interface Props {
  eventId: string;
  open: boolean;
  onClose: () => void;
}

export function EventFlagDialog({ eventId, open, onClose }: Props) {
  const flag = useFlagEvent(eventId);
  const [reason, setReason] = useState('');
  const [reasonError, setReasonError] = useState<string | undefined>(undefined);

  function close() {
    setReason('');
    setReasonError(undefined);
    onClose();
  }

  async function submit() {
    const trimmed = reason.trim();
    if (!trimmed) {
      setReasonError('required');
      return;
    }
    setReasonError(undefined);
    try {
      await flag.mutateAsync({ reason: trimmed });
      toast.success("thanks — we'll take a look 🌱");
      close();
    } catch (err) {
      if (err instanceof FlagEventError && err.kind === 'already-flagged') {
        toast.error("you've already flagged this event");
        close();
        return;
      }
      if (err instanceof FlagEventError && err.kind === 'rate-limited') {
        toast.error(err.message);
        return;
      }
      toast.error("couldn't submit — try again");
    }
  }

  return (
    <Dialog open={open} onClose={close} title="report event">
      <div className="flex flex-col gap-4">
        <p className="text-sm text-neutral-700">what&apos;s wrong with this event?</p>
        <Textarea
          label="reason"
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
          }}
          maxLength={REASON_MAX}
          rows={5}
          error={reasonError}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" onClick={close} disabled={flag.isPending}>
            cancel
          </Button>
          <Button
            onClick={() => {
              void submit();
            }}
            disabled={flag.isPending}
          >
            {flag.isPending ? 'sending…' : 'submit'}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
