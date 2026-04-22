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

// Tailwind `max-h-80` → 20rem → 320px. Kept in sync with the wrapper + img
// classes below so the initial crop math matches what the user sees.
const MAX_PREVIEW_PX = 320;

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
    if (lockedAspect !== undefined) {
      setCrop(
        centerCrop(
          makeAspectCrop({ unit: '%', width: 80 }, lockedAspect, width, height),
          width,
          height,
        ),
      );
      return;
    }
    // Rect (free-form) mode: the image is constrained to MAX_PREVIEW_PX in CSS,
    // so a flat 80%-of-natural crop can overshoot the visible image when the
    // photo is portrait or otherwise taller than the container. Cap the
    // initial crop height at the rendered preview height instead.
    const previewHeight = Math.min(height, MAX_PREVIEW_PX);
    const heightPct = Math.min(80, (previewHeight / height) * 80);
    setCrop(centerCrop({ unit: '%', x: 0, y: 0, width: 80, height: heightPct }, width, height));
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
        <div className="flex max-h-80 items-center justify-center overflow-hidden rounded-md bg-neutral-900">
          <ReactCrop {...reactCropProps}>
            <img ref={imgRef} src={src} alt="" onLoad={onImageLoad} className="max-h-80 w-auto" />
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
