import { useState } from 'react';

import type { EventSpeech, EventSpeechSave, SpeechValues } from '@/api/eventSpeech';
import { SPEECH_BLANKS, type SpeechBlankKey } from '@/components/RichEditor/SpeechBlankExtension';
import { Button } from '@/components/ui/Button';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import { EventFormat } from '@/models/event';

const SHARED_KEYS: SpeechBlankKey[] = [
  'facilitators',
  'open_roles',
  'upcoming_events',
  'intro_question',
];

const FORMAT_KEYS: Record<EventFormat, SpeechBlankKey[]> = {
  walk: ['front_walker', 'back_walker', 'walk_details'],
  restaurant: ['restaurant'],
};

const FORMAT_OPTIONS = [
  { value: EventFormat.Walk, label: 'walk' },
  { value: EventFormat.Restaurant, label: 'restaurant' },
];

function toText(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value.join('\n');
  return value ?? '';
}

function toValue(key: SpeechBlankKey, text: string): string | string[] {
  if (!SPEECH_BLANKS[key].isList) return text.trim();
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

interface Props {
  speech: EventSpeech;
  saving: boolean;
  error: string | null;
  onSave: (input: EventSpeechSave) => void;
  onCancel?: (() => void) | undefined;
}

export function EventSpeechForm({ speech, saving, error, onSave, onCancel }: Props) {
  const formatIsLocked = speech.eventFormat !== null;
  const [format, setFormat] = useState<EventFormat | null>(speech.eventFormat);
  const [texts, setTexts] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(speech.values).map(([k, v]) => [k, toText(v)])),
  );

  const keys = format ? [...SHARED_KEYS, ...FORMAT_KEYS[format]] : [];

  function submit() {
    if (!format) return;
    const values: SpeechValues = {};
    for (const key of keys) values[key] = toValue(key, texts[key] ?? '');
    onSave(formatIsLocked ? { values } : { eventFormat: format, values });
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      {formatIsLocked ? null : (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">is this a walk or a restaurant?</p>
          <SegmentedControl
            name="speech-format"
            ariaLabel="event format"
            className="self-start"
            options={FORMAT_OPTIONS}
            value={format}
            onChange={setFormat}
          />
        </div>
      )}
      {keys.map((key) => (
        <BlankField
          key={key}
          blankKey={key}
          value={texts[key] ?? ''}
          onChange={(text) => {
            setTexts((prev) => ({ ...prev, [key]: text }));
          }}
        />
      ))}
      {error ? (
        <p role="alert" className="text-destructive text-sm">
          {error}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={!format || saving}>
          {saving ? 'saving…' : 'save'}
        </Button>
        {onCancel ? (
          <Button variant="secondary" onClick={onCancel}>
            cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}

function BlankField({
  blankKey,
  value,
  onChange,
}: {
  blankKey: SpeechBlankKey;
  value: string;
  onChange: (text: string) => void;
}) {
  const { label, isList } = SPEECH_BLANKS[blankKey];
  if (isList) {
    return (
      <Textarea
        label={label}
        hint="one per line"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
        }}
      />
    );
  }
  return (
    <TextField
      label={label}
      value={value}
      onChange={(e) => {
        onChange(e.target.value);
      }}
    />
  );
}
