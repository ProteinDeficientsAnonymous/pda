import 'react-image-crop/dist/ReactCrop.css';

import type { SyntheticEvent } from 'react';
import { useEffect, useRef, useState } from 'react';
import ReactCrop, { type Crop, type PercentCrop, type PixelCrop } from 'react-image-crop';

import { cn } from '@/utils/cn';
import { cropImage } from '@/utils/cropImage';

import {
  coverCrop,
  defaultCoverAspect,
  initialCrop,
  MAX_PREVIEW_PX,
  percentToPixelCrop,
  PORTRAIT_ASPECT,
  SQUARE_ASPECT,
} from './initialCrop';
import { Button } from './ui/Button';

export type CropShape = 'round' | 'rect';

const COVER_OPTIONS: { label: string; aspect: number }[] = [
  { label: 'square', aspect: SQUARE_ASPECT },
  { label: '4:5', aspect: PORTRAIT_ASPECT },
];

interface Props {
  file: File;
  shape?: CropShape;
  outputSize?: number;
  onCancel: () => void;
  onCrop: (blob: Blob) => Promise<void> | void;
}

export function ImageCropDialog({
  file,
  shape = 'round',
  outputSize = 512,
  onCancel,
  onCrop,
}: Props) {
  const [src] = useState(() => URL.createObjectURL(file));
  const [crop, setCrop] = useState<Crop | undefined>(undefined);
  const [aspect, setAspect] = useState(shape === 'round' ? 1 : SQUARE_ASPECT);
  const [completed, setCompleted] = useState<PixelCrop | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    return () => {
      URL.revokeObjectURL(src);
    };
  }, [src]);

  function onImageLoad(e: SyntheticEvent<HTMLImageElement>) {
    const { width, height } = e.currentTarget;
    setCrop(initialCrop(width, height, shape));
    if (shape === 'rect') setAspect(defaultCoverAspect(width, height));
  }

  function selectAspect(next: number) {
    const img = imgRef.current;
    setAspect(next);
    if (!img) return;
    const nextCrop = coverCrop(img.width, img.height, next);
    setCrop(nextCrop);
    setCompleted(percentToPixelCrop(nextCrop, img.width, img.height));
  }

  async function handleSave() {
    const img = imgRef.current;
    if (!completed || !img) return;
    const scaleX = img.naturalWidth / img.width;
    const scaleY = img.naturalHeight / img.height;
    const area = {
      x: completed.x * scaleX,
      y: completed.y * scaleY,
      width: completed.width * scaleX,
      height: completed.height * scaleY,
    };
    setSaving(true);
    setError(null);
    try {
      const blob = await cropImage(file, area, outputSize);
      await onCrop(blob);
    } catch {
      setError("couldn't process that photo — try again");
    } finally {
      setSaving(false);
    }
  }

  const reactCropProps = {
    circularCrop: shape === 'round',
    keepSelection: true,
    aspect,
    minWidth: 24,
    onChange: (_: PixelCrop, pct: PercentCrop) => {
      setCrop(pct);
    },
    onComplete: (pixels: PixelCrop) => {
      setCompleted(pixels);
    },
    ...(crop !== undefined ? { crop } : {}),
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="crop photo"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="bg-surface flex w-full max-w-md flex-col gap-4 rounded-lg p-4 shadow-xl">
        <div className="flex items-center justify-center rounded-md bg-neutral-900">
          {/* Cap height on .ReactCrop itself — a wrapper cap would clip a tall image
              instead of scaling it, letting the crop drag off-screen (issue 428). */}
          <ReactCrop {...reactCropProps} style={{ maxHeight: MAX_PREVIEW_PX }}>
            <img ref={imgRef} src={src} alt="" onLoad={onImageLoad} className="w-auto" />
          </ReactCrop>
        </div>
        {shape === 'rect' ? (
          <div className="flex justify-center gap-2" role="group" aria-label="crop shape">
            {COVER_OPTIONS.map((opt) => (
              <button
                key={opt.label}
                type="button"
                aria-pressed={aspect === opt.aspect}
                onClick={() => {
                  selectAspect(opt.aspect);
                }}
                className={cn(
                  'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
                  aspect === opt.aspect
                    ? 'bg-brand-600 text-white'
                    : 'bg-surface-raised text-foreground-secondary hover:bg-brand-50',
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        ) : null}
        {error ? (
          <p role="alert" className="text-xs text-red-600">
            {error}
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel} disabled={saving}>
            cancel
          </Button>
          <Button onClick={() => void handleSave()} disabled={!completed || saving}>
            {saving ? 'saving…' : 'save'}
          </Button>
        </div>
      </div>
    </div>
  );
}
