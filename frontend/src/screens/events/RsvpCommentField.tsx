import { Textarea } from '@/components/ui/Textarea';

export const RSVP_COMMENT_MAX_LENGTH = 300;

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function RsvpCommentField({ value, onChange, disabled = false }: Props) {
  const remaining = RSVP_COMMENT_MAX_LENGTH - value.length;
  return (
    <Textarea
      id="rsvp-comment"
      label="comment (optional)"
      rows={2}
      value={value}
      maxLength={RSVP_COMMENT_MAX_LENGTH}
      disabled={disabled}
      placeholder="bringing snacks? running late? let people know"
      hint={`${String(remaining)} characters left`}
      className="resize-none"
      onChange={(e) => {
        onChange(e.target.value);
      }}
    />
  );
}
