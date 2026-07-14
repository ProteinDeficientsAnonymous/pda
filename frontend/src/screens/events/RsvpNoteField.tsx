// Optional note attached to your RSVP (issue #297) — a controlled textarea
// used inside the RSVP box. The note is posted once (as a comment for
// going/maybe, or a host notification for can't-go); it is not editable later.

export const RSVP_NOTE_MAX_LENGTH = 300;

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function RsvpNoteField({ value, onChange, disabled = false }: Props) {
  const remaining = RSVP_NOTE_MAX_LENGTH - value.length;
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="rsvp-note" className="text-foreground text-sm font-medium">
        note (optional)
      </label>
      <textarea
        id="rsvp-note"
        rows={2}
        value={value}
        maxLength={RSVP_NOTE_MAX_LENGTH}
        disabled={disabled}
        placeholder="bringing snacks? running late? let people know"
        aria-describedby="rsvp-note-remaining"
        onChange={(e) => {
          onChange(e.target.value);
        }}
        className="focus:border-brand-500 focus:ring-brand-200 border-border-strong bg-surface w-full resize-none rounded-md border px-3 py-2 text-sm transition-colors outline-none focus:ring-2"
      />
      <p id="rsvp-note-remaining" className="text-muted text-xs">
        {remaining} characters left
      </p>
    </div>
  );
}
