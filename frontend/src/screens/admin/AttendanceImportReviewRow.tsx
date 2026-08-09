import { useState } from 'react';

import { type ImportRow } from '@/api/attendanceImport';
import { type MemberSearchResult, useUserSearch } from '@/api/userSearch';
import { Button } from '@/components/ui/Button';
import { formatPhone } from '@/utils/formatPhone';

interface Props {
  row: ImportRow;
  resolution: {
    userId: string | null;
    skip: boolean;
    pickedFullName?: string | null | undefined;
  };
  onResolve: (userId: string | null, skip: boolean, fullName?: string | null) => void;
}

export function AttendanceImportReviewRow({ row, resolution, onResolve }: Props) {
  const [term, setTerm] = useState('');
  const { data: searchResults = [] } = useUserSearch(term);
  const resolvedName = resolvedUserName(row, resolution.userId, resolution.pickedFullName);

  if (resolution.skip) {
    return (
      <RowShell row={row}>
        <span className="text-muted text-xs italic">skipped</span>
        <Button
          variant="ghost"
          className="h-7 px-2 text-xs"
          onClick={() => {
            onResolve(null, false);
          }}
        >
          undo
        </Button>
      </RowShell>
    );
  }

  if (resolvedName) {
    return (
      <RowShell row={row}>
        <span className="text-foreground text-xs">
          → {resolvedName.toLowerCase()}
          {row.hasExistingRsvp ? (
            <span className="text-warning ml-1">(overwrites existing rsvp)</span>
          ) : null}
        </span>
        <Button
          variant="ghost"
          className="h-7 px-2 text-xs"
          onClick={() => {
            onResolve(null, false);
          }}
        >
          change
        </Button>
      </RowShell>
    );
  }

  return (
    <div className="border-border bg-surface flex flex-col gap-2 rounded-lg border p-3">
      <div className="flex items-center justify-between gap-3">
        <RowLabel row={row} />
        <Button
          variant="ghost"
          className="h-7 px-2 text-xs"
          onClick={() => {
            onResolve(null, true);
          }}
        >
          skip
        </Button>
      </div>
      {row.candidates.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {row.candidates.map((c) => (
            <button
              key={c.userId}
              type="button"
              onClick={() => {
                onResolve(c.userId, false);
              }}
              className="bg-surface-dim hover:bg-background rounded-full px-2.5 py-1 text-xs"
            >
              {c.fullName.toLowerCase()} · {formatPhone(c.phoneNumber)}
            </button>
          ))}
        </div>
      ) : null}
      <SearchPicker
        term={term}
        onTermChange={setTerm}
        results={searchResults}
        onPick={(u) => {
          onResolve(u.id, false, u.fullName);
        }}
      />
    </div>
  );
}

function RowShell({ row, children }: { row: ImportRow; children: React.ReactNode }) {
  return (
    <div className="border-border bg-surface flex items-center justify-between gap-3 rounded-lg border p-3">
      <RowLabel row={row} />
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}

function RowLabel({ row }: { row: ImportRow }) {
  return (
    <div className="min-w-0 flex-1">
      <p className="text-foreground truncate text-sm font-medium">{row.rawName}</p>
      <p className="text-foreground-tertiary truncate text-xs">
        {row.partifulStatus.toLowerCase()} · {row.checkedIn ? 'checked in' : 'not checked in'}
      </p>
    </div>
  );
}

function resolvedUserName(
  row: ImportRow,
  userId: string | null,
  pickedFullName?: string | null,
): string | null {
  if (!userId) return null;
  if (userId === row.matchedUserId) return row.matchedFullName;
  return row.candidates.find((c) => c.userId === userId)?.fullName ?? pickedFullName ?? 'selected';
}

function SearchPicker({
  term,
  onTermChange,
  results,
  onPick,
}: {
  term: string;
  onTermChange: (v: string) => void;
  results: MemberSearchResult[];
  onPick: (u: MemberSearchResult) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <input
        value={term}
        onChange={(e) => {
          onTermChange(e.target.value);
        }}
        placeholder="search members by name or phone"
        aria-label={`search a member to match "${term}"`}
        className="border-border-strong bg-background h-8 w-full rounded-md border px-2 text-xs outline-none"
      />
      {term.trim().length >= 2 && results.length > 0 ? (
        <ul className="border-border max-h-32 overflow-y-auto rounded-md border">
          {results.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                onClick={() => {
                  onPick(m);
                }}
                className="hover:bg-background flex w-full items-center justify-between px-2 py-1 text-start text-xs"
              >
                <span>{m.fullName.toLowerCase()}</span>
                <span className="text-muted">{formatPhone(m.phoneNumber)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
