// Crop dialog for avatar uploads (circular) and event covers (rectangular).
// Built on react-easy-crop. Returns a PNG blob via onCrop.

import { useCallback, useState } from 'react';
import Cropper, { type Area } from 'react-easy-crop';
import { cropImage } from '@/utils/cropImage';
import { Button } from './ui/Button';

export type CropShape = 'round' | 'rect';

interface Props {
  file: File;
  shape?: CropShape;
  aspect?: number;
  outputSize?: number;
  onCancel: () => void;
  onCrop: (blob: Blob) => Promise<void> | void;
}

export function ImageCropDialog({
  file,
  shape = 'round',
  aspect = 1,
  outputSize = 512,
  onCancel,
  onCrop,
}: Props) {
  const [src] = useState(() => URL.createObjectURL(file));
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [area, setArea] = useState<Area | null>(null);
  const [saving, setSaving] = useState(false);

  const onCropComplete = useCallback((_croppedArea: Area, pixels: Area) => {
    setArea(pixels);
  }, []);

  async function handleSave() {
    if (!area) return;
    setSaving(true);
    try {
      const blob = await cropImage(file, area, outputSize);
      await onCrop(blob);
      URL.revokeObjectURL(src);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="crop photo"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="flex w-full max-w-md flex-col gap-4 rounded-lg bg-white p-4 shadow-xl">
        <div className="relative h-80 overflow-hidden rounded-md bg-neutral-900">
          <Cropper
            image={src}
            crop={crop}
            zoom={zoom}
            aspect={aspect}
            cropShape={shape}
            showGrid={false}
            onCropChange={setCrop}
            onZoomChange={setZoom}
            onCropComplete={onCropComplete}
          />
        </div>
        <label className="flex items-center gap-3 text-sm">
          <span className="w-12 text-neutral-600">zoom</span>
          <input
            type="range"
            min={1}
            max={3}
            step={0.05}
            value={zoom}
            onChange={(e) => {
              setZoom(Number(e.target.value));
            }}
            className="flex-1"
            aria-label="zoom"
          />
        </label>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel} disabled={saving}>
            cancel
          </Button>
          <Button onClick={() => void handleSave()} disabled={!area || saving}>
            {saving ? 'saving…' : 'save'}
          </Button>
        </div>
      </div>
    </div>
  );
}
