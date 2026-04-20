// Async autocomplete that selects multiple members by id. Used for the event
// form's co-host and invited-user pickers.

import { useState } from 'react';
import { useUserSearch, type MemberSearchResult } from '@/api/userSearch';
import { TextField } from './ui/TextField';
import { cn } from '@/utils/cn';

interface Props {
  label: string;
  selected: MemberSearchResult[];
  onChange: (selected: MemberSearchResult[]) => void;
  hint?: string;
  /** User ids to exclude from results (e.g. the current user, existing co-hosts). */
  excludeIds?: readonly string[];
}

export function MemberPicker({ label, selected, onChange, hint, excludeIds = [] }: Props) {
  const [term, setTerm] = useState('');
  const { data = [] } = useUserSearch(term);

  const excluded = new Set<string>([...excludeIds, ...selected.map((m) => m.id)]);
  const results = data.filter((m) => !excluded.has(m.id));

  function pick(m: MemberSearchResult) {
    onChange([...selected, m]);
    setTerm('');
  }

  function remove(id: string) {
    onChange(selected.filter((m) => m.id !== id));
  }

  return (
    <div className="flex flex-col gap-2">
      <TextField
        label={label}
        value={term}
        onChange={(e) => {
          setTerm(e.target.value);
        }}
        placeholder="search by name or phone"
        hint={hint}
      />
      {term.trim().length >= 2 && results.length > 0 ? (
        <ul className="border-border bg-surface max-h-48 overflow-y-auto rounded-md border">
          {results.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                onClick={() => {
                  pick(m);
                }}
                className="hover:bg-background flex w-full items-center justify-between px-3 py-2 text-start text-sm"
              >
                <span>{m.displayName}</span>
                <span className="text-muted text-xs">{m.phoneNumber}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      {selected.length > 0 ? (
        <div className="flex flex-wrap gap-2" aria-label={`selected ${label}`}>
          {selected.map((m) => (
            <span
              key={m.id}
              className={cn(
                'bg-surface-dim inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs',
              )}
            >
              {m.displayName}
              <button
                type="button"
                onClick={() => {
                  remove(m.id);
                }}
                aria-label={`remove ${m.displayName}`}
                className="text-muted hover:text-foreground ms-1"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
