// Hero cover photo for the event form. The whole banner is one big button —
// tap anywhere to pick. Crop happens via the shared ImageCropDialog, which
// lets the user freely drag/resize a crop box over the image.
// On create the cropped blob is staged and uploaded after the event POST
// returns an id; on edit it uploads immediately.

import { useRef, useState } from 'react';
import { isAxiosError } from 'axios';
import { ImageCropDialog } from '@/components/ImageCropDialog';
import { cn } from '@/utils/cn';

const ALLOWED_MIME = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/gif',
  'image/heic',
  'image/heif',
];

interface Props {
  photoUrl: string;
  photoUpdatedAt: string | null;
  /** Called with the cropped blob. Callers decide whether to upload now or defer. */
  onCrop: (blob: Blob) => Promise<void>;
  onDelete?: (() => Promise<void>) | undefined;
  disabled?: boolean | undefined;
}

export function EventFormPhoto({ photoUrl, photoUpdatedAt, onCrop, onDelete, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const displayUrl = photoUrl
    ? photoUpdatedAt
      ? `${photoUrl}?v=${encodeURIComponent(photoUpdatedAt)}`
      : photoUrl
    : '';
  const hasPhoto = Boolean(displayUrl);
  const locked = (disabled ?? false) || busy;

  function open() {
    if (!locked) inputRef.current?.click();
  }

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null);
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    if (!ALLOWED_MIME.includes(f.type)) {
      setError('pick a jpeg, png, webp, gif, or heic image');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      setError('photo must be under 10 MB');
      return;
    }
    setFile(f);
  }

  async function handleCrop(blob: Blob) {
    setBusy(true);
    setError(null);
    try {
      await onCrop(blob);
      setFile(null);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!onDelete || locked) return;
    setBusy(true);
    try {
      await onDelete();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED_MIME.join(',')}
        onChange={onPick}
        className="hidden"
        aria-label="choose event photo"
      />

      <button
        type="button"
        onClick={open}
        disabled={locked}
        aria-label={hasPhoto ? 'change cover photo' : 'add a cover photo'}
        className={cn(
          'group relative aspect-video w-full overflow-hidden rounded-[var(--radius-md)]',
          'focus-visible:ring-brand-300 focus-visible:ring-2 focus-visible:outline-none',
          hasPhoto ? 'bg-surface-raised' : 'border-brand-200 bg-brand-50 border-2 border-dashed',
          locked && 'cursor-not-allowed opacity-60',
        )}
      >
        {hasPhoto ? (
          <>
            <img src={displayUrl} alt="" className="absolute inset-0 h-full w-full object-cover" />
            <div className="absolute inset-0 flex items-end justify-end bg-gradient-to-t from-black/40 via-transparent to-transparent p-3 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
              <span className="text-foreground rounded-full bg-white/90 px-3 py-1 text-xs font-medium">
                change photo
              </span>
            </div>
          </>
        ) : (
          <span className="text-brand-700 absolute inset-0 flex flex-col items-center justify-center gap-2">
            <span aria-hidden="true" className="text-3xl">
              📸
            </span>
            <span className="text-sm font-medium">add a cover photo</span>
            <span className="text-brand-600/80 text-xs">tap to pick — landscape to portrait</span>
          </span>
        )}
      </button>

      {hasPhoto && onDelete ? (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={(e) => void handleDelete(e)}
            disabled={locked}
            className="text-muted hover:text-destructive text-xs underline decoration-dotted disabled:cursor-not-allowed"
          >
            remove photo
          </button>
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="text-destructive text-xs">
          {error}
        </p>
      ) : null}

      {file ? (
        <ImageCropDialog
          file={file}
          shape="rect"
          outputSize={1200}
          onCancel={() => {
            setFile(null);
          }}
          onCrop={handleCrop}
        />
      ) : null}
    </div>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't upload photo — try again";
}
