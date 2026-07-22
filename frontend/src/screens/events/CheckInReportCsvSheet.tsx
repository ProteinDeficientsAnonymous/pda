import { useState } from 'react';
import { toast } from 'sonner';

import { CSV_COLUMNS, downloadCheckInReportCsv } from '@/api/eventCheckInReport';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

const DEFAULT_COLUMNS = new Set<string>(CSV_COLUMNS.map((c) => c.key));

interface Props {
  eventId: string;
  open: boolean;
  onClose: () => void;
}

export function CheckInReportCsvSheet({ eventId, open, onClose }: Props) {
  const [selected, setSelected] = useState<Set<string>>(DEFAULT_COLUMNS);
  const [isDownloading, setIsDownloading] = useState(false);

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function handleDownload() {
    setIsDownloading(true);
    try {
      await downloadCheckInReportCsv(eventId, [...selected]);
      onClose();
    } catch {
      toast.error("couldn't download the csv — try again");
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="download csv">
      <fieldset className="mb-4 flex flex-col gap-2">
        <legend className="sr-only">columns to include</legend>
        {CSV_COLUMNS.map((col) => (
          <label key={col.key} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected.has(col.key)}
              onChange={() => {
                toggle(col.key);
              }}
              className="h-4 w-4"
            />
            {col.label}
          </label>
        ))}
      </fieldset>
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          cancel
        </Button>
        <Button
          onClick={() => {
            void handleDownload();
          }}
          disabled={selected.size === 0 || isDownloading}
        >
          {isDownloading ? 'downloading…' : 'download'}
        </Button>
      </div>
    </Dialog>
  );
}
