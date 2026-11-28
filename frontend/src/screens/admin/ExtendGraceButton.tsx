import { format } from 'date-fns';
import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  type MemberAttendanceRow,
  useExtendAttendanceGrace,
} from '@/api/memberAttendanceAnalytics';
import { Button } from '@/components/ui/Button';
import { DatePicker } from '@/components/ui/DatePicker';
import { Dialog } from '@/components/ui/Dialog';

const ISO_DAY = 'yyyy-MM-dd';

export function ExtendGraceButton({ row }: { row: MemberAttendanceRow }) {
  const [open, setOpen] = useState(false);
  const [graceUntil, setGraceUntil] = useState<string | null>(format(row.deadline, ISO_DAY));
  const extend = useExtendAttendanceGrace(row.userId);
  const name = row.fullName.toLowerCase();

  async function onSave() {
    if (!graceUntil) return;
    try {
      await extend.mutateAsync(graceUntil);
      toast.success('grace extended ✓');
      setOpen(false);
    } catch (err) {
      toast.error(extractApiErrorOr(err, "couldn't extend grace — try again"));
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
        }}
        className="text-foreground-secondary mt-3 text-xs font-medium hover:underline"
      >
        extend grace
      </button>
      <Dialog
        open={open}
        onClose={() => {
          setOpen(false);
        }}
        title={`extend grace for ${name}`}
      >
        <p className="text-muted mb-3 text-sm">
          they won't show as a pause candidate, and reminders won't come due, before this date.
        </p>
        <DatePicker label="new deadline" value={graceUntil} onChange={setGraceUntil} />
        <div className="mt-4 flex justify-end">
          <Button onClick={() => void onSave()} disabled={!graceUntil || extend.isPending}>
            save
          </Button>
        </div>
      </Dialog>
    </>
  );
}
