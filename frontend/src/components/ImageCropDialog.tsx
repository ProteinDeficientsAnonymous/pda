// Crop dialog for avatar uploads (circular) and event covers (rectangular).
// The user drags/resizes a crop box over a stationary image — the common
// Instagram/Facebook/macOS-style UX. Built on react-image-crop. Round shape
// is locked to a 1:1 square (circular mask); rect shape is free-form so the
// box can be reshaped to any ratio by dragging its handles. Returns a PNG
// blob via onCrop.

import { useRef, useState } from 'react';
import ReactCrop, {
  centerCrop,
  makeAspectCrop,
  type Crop,
  type PercentCrop,
  type PixelCrop,
} from 'react-image-crop';
import 'react-image-crop/dist/ReactCrop.css';
import { cropImage } from '@/utils/cropImage';
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
    const next: PercentCrop =
      lockedAspect !== undefined
        ? centerCrop(
            makeAspectCrop({ unit: '%', width: 80 }, lockedAspect, width, height),
            width,
            height,
          )
        : centerCrop({ unit: '%', x: 0, y: 0, width: 80, height: 80 }, width, height);
    setCrop(next);
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
      <div className="flex w-full max-w-md flex-col gap-4 rounded-lg bg-surface p-4 shadow-xl">
        <div className="flex max-h-80 items-center justify-center overflow-hidden rounded-md bg-neutral-900">
          <ReactCrop {...reactCropProps}>
            <img
              ref={imgRef}
              src={src}
              alt=""
              onLoad={onImageLoad}
              className="max-h-80 w-auto"
            />
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
