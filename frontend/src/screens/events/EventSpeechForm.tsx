import { useState } from 'react';

import type { EventSpeech } from '@/api/eventSpeech';
import { SPEECH_BLANKS, type SpeechBlankKey } from '@/components/RichEditor/SpeechBlankExtension';
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

interface Props {
  speech: EventSpeech;
}

export function EventSpeechForm({ speech }: Props) {
  const kind = speech.officialKind;
  const [texts, setTexts] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(speech.values).map(([k, v]) => [k, toText(v)])),
  );

  const keys = kind ? [...SHARED_KEYS, ...KIND_KEYS[kind]] : [];

  return (
    <form className="flex flex-col gap-4">
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
