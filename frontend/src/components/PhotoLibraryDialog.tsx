import type { ChangeEvent, DragEvent } from 'react';
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { type GiphyResult, searchGifs } from '@/api/giphy';
import { cn } from '@/utils/cn';

import { Button } from './ui/Button';
import { SegmentedControl } from './ui/SegmentedControl';

type Tab = 'library' | 'upload';

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

function validateUpload(f: File): string | null {
  if (!ALLOWED_MIME.includes(f.type)) return TYPE_ERROR;
  if (f.size > MAX_PHOTO_BYTES) return SIZE_ERROR;
  return null;
}

interface Props {
  onCancel: () => void;
  /** crop=false for library picks (preserve animation); crop=true for uploads. */
  onSelect: (file: File, opts: { crop: boolean }) => void;
}

async function toFile(gif: GiphyResult): Promise<File> {
  const res = await fetch(gif.originalUrl);
  const blob = await res.blob();
  const type = blob.type || 'image/gif';
  const ext = type.split('/')[1] ?? 'gif';
  return new File([blob], `${gif.id}.${ext}`, { type });
}

export function PhotoLibraryDialog({ onCancel, onSelect }: Props) {
  const [tab, setTab] = useState<Tab>('library');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GiphyResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const dragDepthRef = useRef(0);

  async function runSearch(text: string) {
    setSearching(true);
    try {
      const found = await searchGifs(text);
      setResults(found);
      setError(null);
    } catch {
      setResults([]);
      setError("couldn't search images — try again");
    } finally {
      setSearching(false);
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => void runSearch(''), 0);
    return () => {
      clearTimeout(timer);
    };
  }, []);

  function handleInput(text: string) {
    setQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => void runSearch(text), 400);
  }

  async function pickLibrary(gif: GiphyResult) {
    setPicking(true);
    try {
      const file = await toFile(gif);
      onSelect(file, { crop: false });
    } catch {
      setError("couldn't load that image — try another");
      setPicking(false);
    }
  }

  function acceptUpload(f: File) {
    const err = validateUpload(f);
    if (err) {
      setError(err);
      return;
    }
    onSelect(f, { crop: true });
  }

  function onFilePick(e: ChangeEvent<HTMLInputElement>) {
    setError(null);
    const f = e.target.files?.[0];
    e.target.value = '';
    if (f) acceptUpload(f);
  }

  // Only treat drags carrying files as drop targets — ignore text/HTML drags.
  function isFileDrag(e: DragEvent): boolean {
    return Array.from(e.dataTransfer.types).includes('Files');
  }

  function onDragEnter(e: DragEvent) {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepthRef.current += 1;
    setDragOver(true);
  }

  function onDragOver(e: DragEvent) {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }

  function onDragLeave(e: DragEvent) {
    if (!isFileDrag(e)) return;
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) setDragOver(false);
  }

  function onDrop(e: DragEvent) {
    if (!isFileDrag(e)) return;
    e.preventDefault();
    dragDepthRef.current = 0;
    setDragOver(false);
    setError(null);
    const f = e.dataTransfer.files[0];
    if (f) acceptUpload(f);
  }

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="choose an image"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="bg-surface flex w-full max-w-md flex-col gap-3 rounded-lg p-4 shadow-xl">
        <SegmentedControl<Tab>
          name="photo-picker-tab"
          ariaLabel="choose an image source"
          value={tab}
          onChange={(next) => {
            setError(null);
            setTab(next);
          }}
          options={[
            { value: 'library', label: 'library' },
            { value: 'upload', label: 'upload your own' },
          ]}
          className="self-center"
        />

        {tab === 'library' ? (
          <>
            <input
              type="text"
              value={query}
              onChange={(e) => {
                handleInput(e.target.value);
              }}
              placeholder="search gifs and photos"
              disabled={picking}
              className="border-border bg-background text-foreground rounded-[var(--radius-md)] border px-3 py-2 text-sm"
            />

            <div className="grid max-h-80 grid-cols-3 gap-2 overflow-y-auto">
              {results.map((gif) => (
                <button
                  key={gif.id}
                  type="button"
                  onClick={() => void pickLibrary(gif)}
                  disabled={picking}
                  aria-label={gif.title || 'select image'}
                  className="focus-visible:ring-brand-300 relative aspect-[4/5] w-full overflow-hidden rounded-[var(--radius-md)] focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <img
                    src={gif.previewUrl}
                    alt=""
                    className="absolute inset-0 h-full w-full object-cover"
                  />
                </button>
              ))}
            </div>

            {searching ? <p className="text-foreground/60 text-xs">searching…</p> : null}
            {!searching && query.trim().length > 0 && results.length === 0 && !error ? (
              <p className="text-foreground/60 text-xs">nothing found — try another search</p>
            ) : null}
          </>
        ) : (
          <>
            <input
              ref={inputRef}
              type="file"
              accept={ALLOWED_MIME.join(',')}
              onChange={onFilePick}
              className="hidden"
              aria-label="choose event photo"
            />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragEnter={onDragEnter}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              className={cn(
                'border-brand-200 bg-brand-50 text-brand-700 flex aspect-[4/5] w-full flex-col items-center justify-center gap-2 rounded-[var(--radius-md)] border-2 border-dashed',
                'focus-visible:ring-brand-300 focus-visible:ring-2 focus-visible:outline-none',
                dragOver && 'border-brand-500 ring-brand-300 ring-2',
              )}
            >
              <span className="text-sm font-medium">tap or drop a photo</span>
            </button>
          </>
        )}

        {error ? (
          <p role="alert" className="text-destructive text-xs">
            {error}
          </p>
        ) : null}

        <div className="flex justify-end">
          <Button variant="ghost" onClick={onCancel} disabled={picking}>
            cancel
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
