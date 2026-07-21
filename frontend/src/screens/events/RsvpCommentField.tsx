import type { KeyboardEvent } from 'react';

import { Textarea } from '@/components/ui/Textarea';

export const RSVP_COMMENT_MAX_LENGTH = 300;

interface Props {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  onSubmitShortcut?: () => void;
}

export function RsvpCommentField({ value, onChange, disabled = false, onSubmitShortcut }: Props) {
  const remaining = RSVP_COMMENT_MAX_LENGTH - value.length;

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSubmitShortcut?.();
    }
  }

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
      onKeyDown={handleKeyDown}
    />
  );
}
