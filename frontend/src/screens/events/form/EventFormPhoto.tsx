import { useState } from 'react';

import { extractApiErrorOr } from '@/api/apiErrors';
import { ImageCropDialog } from '@/components/ImageCropDialog';
import { PhotoLibraryDialog } from '@/components/PhotoLibraryDialog';
import { cn } from '@/utils/cn';

interface Props {
  photoUrl: string;
  photoUpdatedAt: string | null;
  /** Called with the final blob. Callers decide whether to upload now or defer. */
  onCrop: (blob: Blob) => Promise<void>;
  disabled?: boolean | undefined;
}

export function EventFormPhoto({ photoUrl, photoUpdatedAt, onCrop, disabled }: Props) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const displayUrl = photoUrl
    ? photoUpdatedAt
      ? `${photoUrl}?v=${encodeURIComponent(photoUpdatedAt)}`
      : photoUrl
    : '';
  const hasPhoto = Boolean(displayUrl);
  const locked = (disabled ?? false) || busy;

  async function upload(blob: Blob) {
    setBusy(true);
    setError(null);
    try {
      await onCrop(blob);
      setCropFile(null);
    } catch (err) {
      setError(extractApiErrorOr(err, "couldn't upload photo — try again"));
    } finally {
      setBusy(false);
    }
  }

  function handleSelect(file: File, opts: { crop: boolean }) {
    setPickerOpen(false);
    setError(null);
    if (opts.crop) {
      setCropFile(file);
      return;
    }
    void upload(file);
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={() => {
          if (!locked) setPickerOpen(true);
        }}
        disabled={locked}
        aria-label={hasPhoto ? 'change event photo' : 'add event photo'}
        className={cn(
          'group relative mx-auto block overflow-hidden rounded-lg',
          'focus-visible:ring-brand-300 focus-visible:ring-2 focus-visible:outline-none',
          // With a photo: shrink-wrap the image so it shows at its own
          // proportions, capped exactly like the detail page (max 70vh tall,
          // 4:5-equivalent width). Empty: fixed 4:5 dashed box.
          hasPhoto
            ? 'w-fit max-w-full'
            : 'border-brand-200 bg-brand-50 aspect-[4/5] w-full border-2 border-dashed',
          locked && 'cursor-not-allowed opacity-60',
        )}
      >
        {hasPhoto ? (
          <>
            <img
              src={displayUrl}
              alt=""
              className="mx-auto block max-h-[70vh] w-auto max-w-[min(100%,calc(70vh*4/5))]"
            />
            <div className="absolute inset-0 flex items-end justify-end bg-gradient-to-t from-black/40 via-transparent to-transparent p-3 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
              <span className="text-foreground rounded-full bg-white/90 px-3 py-1 text-xs font-medium">
                change photo
              </span>
            </div>
          </>
        ) : (
          <span className="text-brand-700 absolute inset-0 flex flex-col items-center justify-center gap-2">
            <span className="text-sm font-medium">add event photo</span>
            <span className="text-brand-600/80 text-xs">tap to choose</span>
          </span>
        )}
      </button>

      {error ? (
        <p role="alert" className="text-destructive text-xs">
          {error}
        </p>
      ) : null}

      {pickerOpen ? (
        <PhotoLibraryDialog
          onCancel={() => {
            setPickerOpen(false);
          }}
          onSelect={handleSelect}
        />
      ) : null}

      {cropFile ? (
        <ImageCropDialog
          file={cropFile}
          shape="rect"
          outputSize={1200}
          onCancel={() => {
            setCropFile(null);
          }}
          onCrop={upload}
        />
      ) : null}
    </div>
  );
}
