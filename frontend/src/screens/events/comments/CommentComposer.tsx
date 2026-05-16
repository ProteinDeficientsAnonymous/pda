import { useState } from 'react';

import { Button } from '@/components/ui/Button';

const MAX = 500;
const WARN = 450;

interface Props {
  onSubmit: (body: string) => void | Promise<void>;
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

  const submit = async () => {
    if (disabled) return;
    const result = onSubmit(trimmed);
    if (result instanceof Promise) {
      try {
        await result;
        setValue('');
      } catch {
        // keep value so the user can retry; the parent should show a toast
      }
    } else {
      setValue('');
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <textarea
        aria-label={label}
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
            void submit();
          }
        }}
        className="focus:border-brand-500 focus:ring-brand-200 border-border-strong bg-surface min-h-[80px] w-full rounded-md border px-3 py-2 text-sm transition-colors outline-none focus:ring-2"
      />
      <div className="flex items-center justify-between">
        <span
          data-testid="comment-char-counter"
          data-state={state}
          className={`text-xs ${counterClass(state)}`}
        >
          {value.length}/{MAX}
        </span>
        <Button
          onClick={() => {
            void submit();
          }}
          disabled={disabled}
        >
          post
        </Button>
      </div>
    </div>
  );
}
