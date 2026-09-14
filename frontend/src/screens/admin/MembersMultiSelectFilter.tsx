import { useEffect, useRef, useState } from 'react';

export function MembersMultiSelectFilter<T extends string>({
  label,
  options,
  selected,
  onChange,
  emptyLabel,
  manyLabel,
}: {
  label: string;
  options: { value: T; label: string }[];
  selected: Set<T>;
  onChange: (next: Set<T>) => void;
  emptyLabel: string;
  manyLabel: (count: number) => string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const summary =
    selected.size === 0
      ? emptyLabel
      : selected.size === 1
        ? (options.find((o) => o.value === [...selected][0])?.label ?? emptyLabel)
        : manyLabel(selected.size);

  function toggle(value: T, checked: boolean) {
    const next = new Set(selected);
    if (checked) next.add(value);
    else next.delete(value);
    onChange(next);
  }

  return (
    <div className="relative flex flex-col gap-1" ref={rootRef}>
      <span className="text-foreground text-sm font-medium">{label}</span>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => {
          setOpen((o) => !o);
        }}
        className="focus:border-brand-500 focus:ring-brand-200 border-border-strong bg-surface flex h-10 w-full items-center justify-between rounded-md border px-3 text-left text-sm transition-colors outline-none focus:ring-2"
      >
        <span className="text-foreground truncate">{summary}</span>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="text-foreground-secondary ml-2 h-4 w-4 shrink-0"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8l4 4 4-4" />
        </svg>
      </button>
      {open ? (
        <div className="border-border-strong bg-surface absolute top-full left-0 z-20 mt-1 w-full rounded-md border p-2 shadow-md">
          <div className="flex max-h-64 flex-col gap-1.5 overflow-y-auto">
            {options.map((option) => (
              <label
                key={option.value}
                className="hover:bg-surface-dim flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 text-sm"
              >
                <input
                  type="checkbox"
                  checked={selected.has(option.value)}
                  onChange={(e) => {
                    toggle(option.value, e.target.checked);
                  }}
                  className="accent-brand-600 h-4 w-4 cursor-pointer rounded"
                />
                <span>{option.label}</span>
              </label>
            ))}
          </div>
          {selected.size > 0 ? (
            <button
              type="button"
              className="text-foreground-secondary mt-2 text-xs hover:underline"
              onClick={() => {
                onChange(new Set());
              }}
            >
              clear
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
