import { useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { type GiphyResult, searchGifs } from '@/api/giphy';

import { Button } from './ui/Button';

interface Props {
  onCancel: () => void;
  onSelect: (file: File) => void;
}

async function toFile(gif: GiphyResult): Promise<File> {
  const res = await fetch(gif.originalUrl);
  const blob = await res.blob();
  return new File([blob], `${gif.id}.gif`, { type: blob.type || 'image/gif' });
}

export function PhotoLibraryDialog({ onCancel, onSelect }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GiphyResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [picking, setPicking] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleInput(text: string) {
    setQuery(text);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (text.trim().length === 0) {
      setResults([]);
      setSearching(false);
      setError(null);
      return;
    }

    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const found = await searchGifs(text);
        setResults(found);
        setError(null);
      } catch {
        setResults([]);
        setError("couldn't search gifs — try again");
      } finally {
        setSearching(false);
      }
    }, 400);
  }

  async function pick(gif: GiphyResult) {
    setPicking(true);
    try {
      const file = await toFile(gif);
      onSelect(file);
    } catch {
      setError("couldn't load that gif — try another");
      setPicking(false);
    }
  }

  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="choose a gif"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="bg-surface flex w-full max-w-md flex-col gap-3 rounded-lg p-4 shadow-xl">
        <p className="text-foreground text-sm font-medium">choose a gif</p>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            handleInput(e.target.value);
          }}
          placeholder="search gifs"
          disabled={picking}
          className="border-border bg-background text-foreground rounded-[var(--radius-md)] border px-3 py-2 text-sm"
        />

        <div className="grid max-h-80 grid-cols-3 gap-2 overflow-y-auto">
          {results.map((gif) => (
            <button
              key={gif.id}
              type="button"
              onClick={() => void pick(gif)}
              disabled={picking}
              aria-label={gif.title || 'select gif'}
              className="focus-visible:ring-brand-300 overflow-hidden rounded-[var(--radius-md)] focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-60"
            >
              <img src={gif.previewUrl} alt="" className="aspect-[4/5] w-full object-cover" />
            </button>
          ))}
        </div>

        {searching ? <p className="text-foreground/60 text-xs">searching…</p> : null}
        {!searching && query.trim().length > 0 && results.length === 0 && !error ? (
          <p className="text-foreground/60 text-xs">no gifs found — try another search</p>
        ) : null}
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
