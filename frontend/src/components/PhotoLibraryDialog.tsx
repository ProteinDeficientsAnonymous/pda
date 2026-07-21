import { createPortal } from 'react-dom';

import { EVENT_LIBRARY_IMAGES, type LibraryImage } from '@/assets/eventLibraryImages';

import { Button } from './ui/Button';

interface Props {
  onCancel: () => void;
  onSelect: (file: File) => void;
}

async function toFile(image: LibraryImage): Promise<File> {
  const res = await fetch(image.dataUrl);
  const blob = await res.blob();
  return new File([blob], `${image.id}.svg`, { type: blob.type });
}

export function PhotoLibraryDialog({ onCancel, onSelect }: Props) {
  async function pick(image: LibraryImage) {
    const file = await toFile(image);
    onSelect(file);
  }

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="choose from library"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="bg-surface flex w-full max-w-md flex-col gap-4 rounded-lg p-4 shadow-xl">
        <p className="text-foreground text-sm font-medium">choose from library</p>
        <div className="grid grid-cols-3 gap-2">
          {EVENT_LIBRARY_IMAGES.map((image) => (
            <button
              key={image.id}
              type="button"
              onClick={() => void pick(image)}
              aria-label={image.label}
              className="focus-visible:ring-brand-300 overflow-hidden rounded-[var(--radius-md)] focus-visible:ring-2 focus-visible:outline-none"
            >
              <img src={image.dataUrl} alt="" className="aspect-[4/5] w-full object-cover" />
            </button>
          ))}
        </div>
        <div className="flex justify-end">
          <Button variant="ghost" onClick={onCancel}>
            cancel
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
