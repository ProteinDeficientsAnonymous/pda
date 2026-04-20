// Location autocomplete field. Type 3+ chars to search via Photon geocode
// API (proxied through backend). On selection, fills the input with a condensed
// lowercase address and fires onChange with location + lat/lng. Free text
// still works — coords stay null if no result is picked.

import { useEffect, useRef, useState } from 'react';
import { searchLocations, type PhotonResult } from '@/api/geocode';

interface Props {
  label: string;
  value: string;
  latitude: number | null;
  longitude: number | null;
  onChange: (patch: {
    location: string;
    latitude: number | null;
    longitude: number | null;
  }) => void;
  disabled?: boolean;
  error?: string | undefined;
  maxLength?: number;
  placeholder?: string;
}

export function LocationField({
  label,
  value,
  onChange,
  disabled,
  error,
  maxLength,
  placeholder,
}: Props) {
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<PhotonResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  // Track the last value the parent set, so we can sync when it changes
  // externally (e.g. form reset) without overwriting user input.
  const [prevValue, setPrevValue] = useState(value);

  if (value !== prevValue) {
    setPrevValue(value);
    setQuery(value);
  }

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('mousedown', onClick);
    };
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  function handleInput(text: string) {
    setQuery(text);
    setOpen(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (text.trim().length < 3) {
      setResults([]);
      setSearching(false);
      onChange({ location: text, latitude: null, longitude: null });
      return;
    }

    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const found = await searchLocations(text);
        setResults(found);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 400);
  }

  function handleSelect(result: PhotonResult) {
    setQuery(result.fullAddress);
    setPrevValue(result.fullAddress);
    setOpen(false);
    setResults([]);
    onChange({ location: result.fullAddress, latitude: result.lat, longitude: result.lon });
  }

  function handleBlur() {
    if (query !== value) {
      setPrevValue(query);
      onChange({ location: query, latitude: null, longitude: null });
    }
  }

  const inputId = `field-${label.replace(/\s+/g, '-').toLowerCase()}`;

  return (
    <div ref={containerRef} className="relative flex flex-col gap-1">
      <label htmlFor={inputId} className="text-foreground text-sm font-medium">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type="text"
          value={query}
          onChange={(e) => {
            handleInput(e.target.value);
          }}
          onBlur={handleBlur}
          onFocus={() => {
            if (results.length > 0) setOpen(true);
          }}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          autoComplete="off"
          maxLength={maxLength}
          placeholder={placeholder}
          className={[
            'bg-surface h-10 w-full rounded-md border px-3 text-sm transition-colors outline-none focus:ring-2',
            'border-border-strong focus:border-brand-500 focus:ring-brand-200',
            error && 'border-destructive-border focus:border-red-500 focus:ring-red-100',
            disabled && 'bg-surface-dim text-muted-foreground',
          ]
            .filter(Boolean)
            .join(' ')}
        />
        {searching && (
          <span className="absolute top-1/2 right-3 -translate-y-1/2">
            <span className="border-border-strong border-t-brand-600 inline-block h-3.5 w-3.5 animate-spin rounded-full border-2" />
          </span>
        )}
      </div>

      {open && results.length > 0 && (
        <ul className="border-border bg-surface absolute top-full right-0 left-0 z-50 mt-1 max-h-56 overflow-auto rounded-[var(--radius-md)] border shadow-(--shadow-lg)">
          {results.map((r, i) => (
            <li key={`${String(r.lat)},${String(r.lon)}-${String(i)}`}>
              <button
                type="button"
                className="hover:bg-brand-50 focus:bg-brand-50 w-full px-3 py-2 text-left text-sm transition-colors focus:outline-none"
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(r);
                }}
              >
                <span className="text-foreground font-medium">{r.name.toLowerCase()}</span>
                {r.subtitle && r.subtitle !== r.name ? (
                  <span className="text-muted ml-1">{r.subtitle.toLowerCase()}</span>
                ) : null}
              </button>
            </li>
          ))}
        </ul>
      )}

      {error ? <p className="text-destructive text-xs">{error}</p> : null}
    </div>
  );
}
