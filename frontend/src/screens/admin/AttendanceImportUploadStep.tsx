import { useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';

interface Props {
  onFileReady: (file: File) => void;
  isPending: boolean;
}

export function AttendanceImportUploadStep({ onFileReady, isPending }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    onFileReady(file);
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-muted text-sm">
        upload the raw partiful attendee export for this event (csv with name, status, checked in
        columns)
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv"
        className="sr-only"
        onChange={handleChange}
        aria-label="partiful csv file"
      />
      <Button variant="secondary" onClick={() => inputRef.current?.click()} disabled={isPending}>
        {fileName ?? 'choose csv file'}
      </Button>
      {isPending ? <p className="text-muted text-sm">reading file…</p> : null}
    </div>
  );
}
