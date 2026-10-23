import { useEffect, useRef, useState } from 'react';

import { QuestionType } from '@/api/questionTypes';
import { Button } from '@/components/ui/Button';
import { DateTimePicker } from '@/components/ui/DateTimePicker';
import { TextField } from '@/components/ui/TextField';
import { cn } from '@/utils/cn';

function OptionMarker({ fieldType, index }: { fieldType: string; index: number }) {
  if (fieldType === QuestionType.Select || fieldType === QuestionType.Rating) {
    return <span className="text-muted w-4 text-end text-sm">{String(index + 1)}.</span>;
  }
  return (
    <span
      aria-hidden="true"
      className={cn(
        'border-foreground-tertiary h-4 w-4 shrink-0 border-2',
        fieldType === QuestionType.Checkbox ? 'rounded-sm' : 'rounded-full',
      )}
    />
  );
}

interface Props {
  id: string;
  fieldType: string;
  options: string[];
  disabled: boolean;
  onChange: (options: string[]) => void;
  onCommit: (options: string[]) => void;
}

export function QuestionCardOptions({
  id,
  fieldType,
  options,
  disabled,
  onChange,
  onCommit,
}: Props) {
  const [focusTarget, setFocusTarget] = useState<{ index: number } | null>(null);
  const focusIndex = focusTarget?.index ?? null;
  const focusRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    focusRef.current?.focus();
  }, [focusTarget]);

  const isPoll = fieldType === QuestionType.DatetimePoll;
  const isRating = fieldType === QuestionType.Rating;
  const rows = options.length === 0 && !isRating ? [''] : options;
  const canRemove = rows.length > 1 || isRating;
  const canAdd = !isRating || rows.length < 5;

  function insertRowAfter(index: number) {
    setFocusTarget({ index: index + 1 });
    onChange([...rows.slice(0, index + 1), '', ...rows.slice(index + 1)]);
  }

  function setRow(index: number, value: string) {
    const next = [...rows];
    next[index] = value;
    return next;
  }

  return (
    <div className="flex flex-col gap-2">
      {isRating ? <p className="text-muted text-xs">optional labels for stars 1–5</p> : null}
      <ul className="flex flex-col gap-2">
        {rows.map((option, index) => {
          const label = isRating
            ? `star ${String(index + 1)} label`
            : `option ${String(index + 1)}`;
          return (
            <li key={index} className="flex items-center gap-2">
              {isPoll ? null : <OptionMarker fieldType={fieldType} index={index} />}
              <div className="min-w-0 flex-1">
                {isPoll ? (
                  <DateTimePicker
                    label={label}
                    value={option || null}
                    disabled={disabled}
                    onChange={(iso) => {
                      onCommit(setRow(index, iso ?? ''));
                    }}
                  />
                ) : (
                  <TextField
                    id={`${id}-option-${String(index)}`}
                    label={label}
                    hideLabel
                    placeholder={label}
                    value={option}
                    disabled={disabled}
                    maxLength={200}
                    ref={focusIndex === index ? focusRef : undefined}
                    onChange={(e) => {
                      onChange(setRow(index, e.target.value));
                    }}
                    onKeyDown={(e) => {
                      if (e.key !== 'Enter' || !canAdd) return;
                      e.preventDefault();
                      insertRowAfter(index);
                    }}
                    onBlur={() => {
                      onCommit(rows);
                    }}
                  />
                )}
              </div>
              {disabled || !canRemove ? null : (
                <Button
                  variant="ghost"
                  aria-label={`remove ${label}`}
                  className={cn('h-9 px-2', isPoll && 'self-end')}
                  onClick={() => {
                    onCommit(rows.filter((_, i) => i !== index));
                  }}
                >
                  ✕
                </Button>
              )}
            </li>
          );
        })}
      </ul>
      {disabled || !canAdd ? null : (
        <Button
          variant="ghost"
          className="h-9 self-start px-2"
          onClick={() => {
            insertRowAfter(rows.length - 1);
          }}
        >
          {isPoll ? '+ add date' : isRating ? '+ add star label' : '+ add option'}
        </Button>
      )}
    </div>
  );
}
