import { useState } from 'react';
import { toast } from 'sonner';

import {
  type AttendanceImportPreview,
  type ImportRow,
  reportAttendanceImportError,
  type RowResolution,
  useCommitAttendanceImport,
  usePreviewAttendanceImport,
} from '@/api/attendanceImport';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

import { AttendanceImportEventStep, type EventTarget } from './AttendanceImportEventStep';
import { AttendanceImportReviewRow } from './AttendanceImportReviewRow';
import { AttendanceImportUploadStep } from './AttendanceImportUploadStep';

type Step = 'event' | 'upload' | 'review';

interface Props {
  open: boolean;
  onClose: () => void;
}

function rowToResolution(row: ImportRow): RowResolution {
  return {
    rowIndex: row.rowIndex,
    rawName: row.rawName,
    partifulStatus: row.partifulStatus,
    checkedIn: row.checkedIn,
    userId: row.matchedUserId,
    skip: false,
  };
}

export function AttendanceImportDialog({ open, onClose }: Props) {
  const [step, setStep] = useState<Step>('event');
  const [target, setTarget] = useState<EventTarget>({});
  const [preview, setPreview] = useState<AttendanceImportPreview | null>(null);
  const [resolutions, setResolutions] = useState<Record<number, RowResolution>>({});
  const [pickedFullNames, setPickedFullNames] = useState<Record<number, string | null>>({});

  const previewMutation = usePreviewAttendanceImport();
  const commitMutation = useCommitAttendanceImport();

  function reset() {
    setStep('event');
    setTarget({});
    setPreview(null);
    setResolutions({});
    setPickedFullNames({});
  }

  function handleClose() {
    reset();
    onClose();
  }

  function handleFileReady(file: File) {
    previewMutation.mutate(
      { file, eventId: target.eventId },
      {
        onSuccess: (result) => {
          setPreview(result);
          const initial: Record<number, RowResolution> = {};
          for (const row of [...result.matched, ...result.needsReview]) {
            initial[row.rowIndex] = rowToResolution(row);
          }
          setResolutions(initial);
          setStep('review');
        },
        onError: (err) => {
          toast.error(reportAttendanceImportError(err));
        },
      },
    );
  }

  function handleCommit() {
    if (!preview) return;
    commitMutation.mutate(
      { ...target, rows: Object.values(resolutions) },
      {
        onSuccess: (result) => {
          toast.success(`imported attendance for ${result.eventTitle.toLowerCase()} ✓`);
          handleClose();
        },
        onError: (err) => {
          toast.error(reportAttendanceImportError(err));
        },
      },
    );
  }

  const allRows = preview ? [...preview.matched, ...preview.needsReview] : [];
  const unresolvedCount = allRows.filter((r) => {
    const res = resolutions[r.rowIndex];
    return !res || (!res.userId && !res.skip);
  }).length;

  return (
    <Dialog open={open} onClose={handleClose} title="import partiful attendance">
      {step === 'event' ? (
        <AttendanceImportEventStep
          onNext={(t) => {
            setTarget(t);
            setStep('upload');
          }}
        />
      ) : null}

      {step === 'upload' ? (
        <AttendanceImportUploadStep
          onFileReady={handleFileReady}
          isPending={previewMutation.isPending}
        />
      ) : null}

      {step === 'review' && preview ? (
        <div className="flex flex-col gap-3">
          <p className="text-muted text-sm">
            {preview.matched.length} matched automatically
            {preview.needsReview.length > 0
              ? `, ${String(preview.needsReview.length)} need review`
              : ''}
          </p>
          <div className="flex max-h-96 flex-col gap-2 overflow-y-auto">
            {allRows.map((row) => (
              <AttendanceImportReviewRow
                key={row.rowIndex}
                row={row}
                resolution={{
                  userId: resolutions[row.rowIndex]?.userId ?? null,
                  skip: resolutions[row.rowIndex]?.skip ?? false,
                  pickedFullName: pickedFullNames[row.rowIndex],
                }}
                onResolve={(userId, skip, fullName) => {
                  setResolutions((prev) => ({
                    ...prev,
                    [row.rowIndex]: { ...rowToResolution(row), userId, skip },
                  }));
                  setPickedFullNames((prev) => ({ ...prev, [row.rowIndex]: fullName ?? null }));
                }}
              />
            ))}
          </div>
          {unresolvedCount > 0 ? (
            <p className="text-muted text-xs">
              {unresolvedCount} row{unresolvedCount === 1 ? '' : 's'} still need a member or skip
            </p>
          ) : null}
          <Button disabled={unresolvedCount > 0 || commitMutation.isPending} onClick={handleCommit}>
            {commitMutation.isPending ? 'importing…' : 'confirm import'}
          </Button>
        </div>
      ) : null}
    </Dialog>
  );
}
