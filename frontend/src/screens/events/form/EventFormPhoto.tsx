import type { ChangeEvent, DragEvent, MouseEvent } from 'react';
import { useRef, useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
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

const MAX_PHOTO_BYTES = 10 * 1024 * 1024;
const TYPE_ERROR = 'pick a jpeg, png, webp, gif, or heic image';
const SIZE_ERROR = 'photo must be under 10 MB';

function validateFile(f: File): string | null {
  if (!ALLOWED_MIME.includes(f.type)) return TYPE_ERROR;
  if (f.size > MAX_PHOTO_BYTES) return SIZE_ERROR;
  return null;
}

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
  const dragDepthRef = useRef(0);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);

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

  function acceptFile(f: File) {
    const err = validateFile(f);
    if (err) {
      setError(err);
      return;
    }
    setFile(f);
  }

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    setError(null);
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    acceptFile(f);
  }

  // Only treat drags carrying files as drop targets — ignore text/HTML drags.
  function isFileDrag(e: DragEvent): boolean {
    return Array.from(e.dataTransfer.types).includes('Files');
  }

  function onDragEnter(e: DragEvent) {
    if (locked || !isFileDrag(e)) return;
    e.preventDefault();
    dragDepthRef.current += 1;
    setDragOver(true);
  }

  function onDragOver(e: DragEvent) {
    if (locked || !isFileDrag(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }

  function onDragLeave(e: DragEvent) {
    if (locked || !isFileDrag(e)) return;
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) setDragOver(false);
  }

  function onDrop(e: DragEvent) {
    if (locked || !isFileDrag(e)) return;
    e.preventDefault();
    dragDepthRef.current = 0;
    setDragOver(false);
    setError(null);
    const f = e.dataTransfer.files[0];
    if (!f) return;
    acceptFile(f);
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

  async function handleDelete(e: MouseEvent) {
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
        onDragEnter={onDragEnter}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        disabled={locked}
        aria-label={hasPhoto ? 'change cover photo' : 'add a cover photo'}
        className={cn(
          'group relative overflow-hidden rounded-[var(--radius-md)]',
          'focus-visible:ring-brand-300 focus-visible:ring-2 focus-visible:outline-none',
          hasPhoto
            ? 'mx-auto block w-auto max-w-full'
            : 'border-brand-200 bg-brand-50 aspect-video w-full border-2 border-dashed',
          dragOver && 'border-brand-500 ring-brand-300 ring-2',
          locked && 'cursor-not-allowed opacity-60',
        )}
      >
        {hasPhoto ? (
          <>
            <img src={displayUrl} alt="" className="mx-auto block max-h-[70vh] w-auto max-w-full" />
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
            <span className="text-brand-600/80 text-xs">tap or drop a photo</span>
          </span>
        )}
        {dragOver ? (
          <div
            aria-hidden="true"
            className="bg-brand-50/90 text-brand-700 pointer-events-none absolute inset-0 flex items-center justify-center text-sm font-medium"
          >
            drop to use this photo
          </div>
        ) : null}
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
  return extractApiErrorOr(err, "couldn't upload photo — try again");
}
