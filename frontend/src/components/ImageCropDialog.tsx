// Crop dialog for avatar uploads (round, 1:1 circular mask) and event covers
// (rect, free-form). Built on react-image-crop; returns a PNG blob via onCrop.

import { useRef, useState } from 'react';
import ReactCrop, { type Crop, type PercentCrop, type PixelCrop } from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';
import { cropImage } from '@/utils/cropImage';
import { initialCrop, percentToPixelCrop, MAX_PREVIEW_PX } from './initialCrop';
import { Button } from './ui/Button';

export type CropShape = 'round' | 'rect';

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
  const lockedAspect = shape === 'round' ? 1 : undefined;
  const [src] = useState(() => URL.createObjectURL(file));
  const [crop, setCrop] = useState<Crop | undefined>(undefined);
  const [completed, setCompleted] = useState<PixelCrop | null>(null);
  const [saving, setSaving] = useState(false);
  const imgRef = useRef<HTMLImageElement | null>(null);

  function onImageLoad(e: React.SyntheticEvent<HTMLImageElement>) {
    const { width, height } = e.currentTarget;
    const pct = initialCrop(width, height, shape);
    setCrop(pct);
    // react-image-crop only fires onComplete on user interaction, so seed the
    // pixel crop from the initial selection. Without this, hitting save before
    // dragging the box is a no-op (handleSave bails on a null completed crop)
    // and no upload request ever fires. See issue 523.
    setCompleted(percentToPixelCrop(pct, width, height));
  }

  function handleCancel() {
    URL.revokeObjectURL(src);
    onCancel();
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
    try {
      const blob = await cropImage(file, area, outputSize);
      await onCrop(blob);
      URL.revokeObjectURL(src);
    } finally {
      setSaving(false);
    }
  }

  const reactCropProps = {
    circularCrop: shape === 'round',
    keepSelection: true,
    minWidth: 24,
    onChange: (_: PixelCrop, pct: PercentCrop) => {
      setCrop(pct);
    },
    onComplete: (pixels: PixelCrop) => {
      setCompleted(pixels);
    },
    ...(crop !== undefined ? { crop } : {}),
    ...(lockedAspect !== undefined ? { aspect: lockedAspect } : {}),
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
          {/* Cap height on .ReactCrop itself, not a wrapper. react-image-crop sets
              `child-wrapper > img { max-height: inherit }`, so only a cap here scales
              a tall image down — a wrapper cap would just clip it and let the crop be
              dragged into the off-screen remainder. See issue 428. */}
          <ReactCrop {...reactCropProps} style={{ maxHeight: MAX_PREVIEW_PX }}>
            <img ref={imgRef} src={src} alt="" onLoad={onImageLoad} className="w-auto" />
          </ReactCrop>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={handleCancel} disabled={saving}>
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
