// Photo upload for an existing event. The create flow can't upload a photo
// until the event exists (backend endpoint is scoped by :id), so the form
// chains create → upload when a photo is staged before save.

import { useRef, useState } from 'react';
import { isAxiosError } from 'axios';
import { ImageCropDialog } from '@/components/ImageCropDialog';
import { Button } from '@/components/ui/Button';

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

  async function handleDelete() {
    if (!onDelete) return;
    setBusy(true);
    try {
      await onDelete();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-xs font-medium tracking-wide text-neutral-500 uppercase">photo</h2>
      {displayUrl ? (
        <img
          src={displayUrl}
          alt=""
          className="aspect-video w-full max-w-md rounded-lg object-cover"
        />
      ) : (
        <div className="flex aspect-video w-full max-w-md items-center justify-center rounded-lg border border-dashed border-neutral-300 bg-neutral-50 text-xs text-neutral-500">
          no photo yet
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <input
          ref={inputRef}
          type="file"
          accept={ALLOWED_MIME.join(',')}
          onChange={onPick}
          className="hidden"
          aria-label="choose event photo"
        />
        <Button
          variant="secondary"
          disabled={(disabled ?? false) || busy}
          onClick={() => inputRef.current?.click()}
        >
          {displayUrl ? 'replace photo' : 'add photo'}
        </Button>
        {displayUrl && onDelete ? (
          <Button
            variant="ghost"
            disabled={(disabled ?? false) || busy}
            onClick={() => void handleDelete()}
          >
            remove
          </Button>
        ) : null}
      </div>
      {error ? (
        <p role="alert" className="text-xs text-red-600">
          {error}
        </p>
      ) : null}
      {file ? (
        <ImageCropDialog
          file={file}
          shape="rect"
          aspect={16 / 9}
          outputSize={1200}
          onCancel={() => {
            setFile(null);
          }}
          onCrop={handleCrop}
        />
      ) : null}
    </section>
  );
}

function extractError(err: unknown): string {
  if (isAxiosError(err)) {
    const detail = (err.response?.data as { detail?: string } | undefined)?.detail;
    if (detail) return detail;
  }
  return "couldn't upload photo — try again";
}
