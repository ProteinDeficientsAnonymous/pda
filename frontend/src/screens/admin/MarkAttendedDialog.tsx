import { useState } from 'react';
import { toast } from 'sonner';

import { reportMarkAttendanceError, useMarkAttendance } from '@/api/attendanceMark';
import type { Member } from '@/api/users';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { formatPhone } from '@/utils/formatPhone';

import { AttendanceImportEventStep, type EventTarget } from './AttendanceImportEventStep';

interface Props {
  open: boolean;
  members: Member[];
  onClose: () => void;
  onMarked: () => void;
}

export function MarkAttendedDialog({ open, members, onClose, onMarked }: Props) {
  const [target, setTarget] = useState<EventTarget | null>(null);
  const mark = useMarkAttendance();

  function handleClose() {
    setTarget(null);
    onClose();
  }

  function handleConfirm() {
    if (!target) return;
    mark.mutate(
      { ...target, userIds: members.map((m) => m.id) },
      {
        onSuccess: (result) => {
          toast.success(`marked attended at ${result.eventTitle.toLowerCase()} ✓`);
          setTarget(null);
          onMarked();
        },
        onError: (err) => {
          toast.error(reportMarkAttendanceError(err));
        },
      },
    );
  }

  return (
    <Dialog open={open} onClose={handleClose} title="mark attended">
      {target === null ? (
        <AttendanceImportEventStep onNext={setTarget} />
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-muted text-sm">
            marking {members.length} {members.length === 1 ? 'member' : 'members'} as attended in
            person
          </p>
          <ul className="border-border bg-surface flex max-h-64 flex-col gap-1 overflow-y-auto rounded-md border p-2 text-sm">
            {members.map((m) => (
              <li key={m.id} className="text-foreground truncate">
                {(m.fullName || formatPhone(m.phoneNumber)).toLowerCase()}
              </li>
            ))}
          </ul>
          <div className="flex justify-between gap-2">
            <Button
              variant="secondary"
              onClick={() => {
                setTarget(null);
              }}
              disabled={mark.isPending}
            >
              back
            </Button>
            <Button onClick={handleConfirm} disabled={mark.isPending}>
              {mark.isPending ? 'marking…' : 'confirm'}
            </Button>
          </div>
        </div>
      )}
    </Dialog>
  );
}
