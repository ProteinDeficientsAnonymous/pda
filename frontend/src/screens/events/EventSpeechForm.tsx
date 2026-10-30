import { useState } from 'react';

import type { EventSpeech, EventSpeechSave, SpeechValues } from '@/api/eventSpeech';
import { SPEECH_BLANKS, type SpeechBlankKey } from '@/components/RichEditor/SpeechBlankExtension';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { TextField } from '@/components/ui/TextField';
import type { OfficialKind } from '@/models/event';

const SHARED_KEYS: SpeechBlankKey[] = [
  'facilitators',
  'open_roles',
  'upcoming_events',
  'intro_question',
];

const KIND_KEYS: Record<OfficialKind, SpeechBlankKey[]> = {
  walk: ['front_walker', 'back_walker', 'walk_details'],
  restaurant: ['restaurant'],
};

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
}

export function EventSpeechForm({ speech, saving, error, onSave }: Props) {
  const kind = speech.officialKind;
  const [texts, setTexts] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(speech.values).map(([k, v]) => [k, toText(v)])),
  );

  const keys = kind ? [...SHARED_KEYS, ...KIND_KEYS[kind]] : [];

  function submit() {
    if (!kind) return;
    const values: SpeechValues = {};
    for (const key of keys) values[key] = toValue(key, texts[key] ?? '');
    onSave({ values });
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
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
        <Button type="submit" disabled={!kind || saving}>
          {saving ? 'saving…' : 'save'}
        </Button>
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
