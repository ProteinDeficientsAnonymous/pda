import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';

const MAX = 500;
const WARN = 450;

interface Props {
  onSubmit: (body: string) => void;
  submitting: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  label?: string;
}

function counterState(length: number): 'ok' | 'warning' | 'over' {
  if (length >= MAX) return 'over';
  if (length >= WARN) return 'warning';
  return 'ok';
}

function counterClass(state: ReturnType<typeof counterState>): string {
  if (state === 'over') return 'text-destructive';
  if (state === 'warning') return 'text-amber-500';
  return 'text-foreground-tertiary';
}

export function CommentComposer({
  onSubmit,
  submitting,
  placeholder = 'say something…',
  autoFocus = false,
  label = 'comment',
}: Props) {
  const [value, setValue] = useState('');
  const trimmed = value.trim();
  const state = counterState(value.length);
  const disabled = submitting || trimmed.length === 0 || state === 'over';

  const submit = () => {
    if (disabled) return;
    onSubmit(trimmed);
    setValue('');
  };

  return (
    <div className="flex flex-col gap-2">
      <Textarea
        label={label}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
        }}
        placeholder={placeholder}
        // eslint-disable-next-line jsx-a11y/no-autofocus
        autoFocus={autoFocus}
        rows={3}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault();
            submit();
          }
        }}
      />
      <div className="flex items-center justify-between">
        <span
          data-testid="comment-char-counter"
          data-state={state}
          className={`text-xs ${counterClass(state)}`}
        >
          {value.length}/{MAX}
        </span>
        <Button onClick={submit} disabled={disabled}>
          post
        </Button>
      </div>
    </div>
  );
}
