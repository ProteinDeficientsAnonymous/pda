// Optional note attached to your RSVP (issue #297) — e.g. "running 10 mins
// late". Explicitly saved rather than auto-saved, so we POST once per edit
// instead of once per keystroke.

import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/Button';

export const RSVP_NOTE_MAX_LENGTH = 300;

interface Props {
  note: string;
  disabled: boolean;
  onSave: (note: string) => void;
}

export function RsvpNoteField({ note, disabled, onSave }: Props) {
  const [draft, setDraft] = useState(note);
  const [editing, setEditing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Focus on open. `autoFocus` is disallowed (jsx-a11y/no-autofocus) because it
  // steals focus on page load; here the field only mounts on an explicit click.
  useEffect(() => {
    if (editing) textareaRef.current?.focus();
  }, [editing]);

  if (!editing) {
    return (
      <div className="flex flex-col items-center gap-1">
        {note ? <p className="text-foreground-secondary text-sm">“{note}”</p> : null}
        <Button
          variant="ghost"
          disabled={disabled}
          onClick={() => {
            setDraft(note);
            setEditing(true);
          }}
        >
          {note ? 'edit your note' : 'add a note'}
        </Button>
      </div>
    );
  }

  const trimmed = draft.trim();
  const remaining = RSVP_NOTE_MAX_LENGTH - draft.length;

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        setEditing(false);
        // Nothing changed — skip the round-trip.
        if (trimmed === note) return;
        onSave(trimmed);
      }}
    >
      <label htmlFor="rsvp-note" className="text-foreground text-sm font-medium">
        note
      </label>
      <textarea
        id="rsvp-note"
        ref={textareaRef}
        rows={2}
        value={draft}
        maxLength={RSVP_NOTE_MAX_LENGTH}
        disabled={disabled}
        placeholder="bringing snacks? running late? let people know"
        aria-describedby="rsvp-note-remaining"
        onChange={(e) => {
          setDraft(e.target.value);
        }}
        className="focus:border-brand-500 focus:ring-brand-200 border-border-strong bg-surface w-full resize-none rounded-md border px-3 py-2 text-sm transition-colors outline-none focus:ring-2"
      />
      <p id="rsvp-note-remaining" className="text-muted text-xs">
        {remaining} characters left
      </p>
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          disabled={disabled}
          onClick={() => {
            setDraft(note);
            setEditing(false);
          }}
        >
          cancel
        </Button>
        <Button type="submit" disabled={disabled}>
          save note
        </Button>
      </div>
    </form>
  );
}
