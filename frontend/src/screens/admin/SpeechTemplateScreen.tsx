import { useState } from 'react';

import { useSpeechTemplate, useUpdateSpeechTemplate } from '@/api/eventSpeech';
import { AutosaveStatus } from '@/components/AutosaveStatus';
import { RichEditor } from '@/components/RichEditor/RichEditor';
import { SpeechBlankExtension } from '@/components/RichEditor/SpeechBlankExtension';
import { SpeechBlankMenu } from '@/components/RichEditor/SpeechBlankMenu';
import { Textarea } from '@/components/ui/Textarea';
import { useAutosave } from '@/hooks/useAutosave';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

const SPEECH_EXTENSIONS = [SpeechBlankExtension];

function parseRoles(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
}

function SectionShell({
  title,
  status,
  children,
  onBlur,
}: {
  title: string;
  status: Parameters<typeof AutosaveStatus>[0]['status'];
  children: React.ReactNode;
  onBlur: () => void;
}) {
  return (
    <section onBlur={onBlur} className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-medium">{title}</h2>
        <AutosaveStatus status={status} />
      </div>
      {children}
    </section>
  );
}

function PmSection({
  title,
  initial,
  onSave,
}: {
  title: string;
  initial: string;
  onSave: (pm: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState(initial);
  const autosave = useAutosave({ onSave });

  return (
    <SectionShell
      title={title}
      status={autosave.status}
      onBlur={() => {
        void autosave.flush(draft);
      }}
    >
      <RichEditor
        value={draft}
        onChange={(next) => {
          setDraft(next);
          autosave.schedule(next);
        }}
        placeholder={title}
        extraExtensions={SPEECH_EXTENSIONS}
        toolbarExtra={(editor) => <SpeechBlankMenu editor={editor} />}
      />
    </SectionShell>
  );
}

function OpenRolesSection({
  initial,
  onSave,
}: {
  initial: string[];
  onSave: (roles: string[]) => Promise<void>;
}) {
  const [text, setText] = useState(initial.join('\n'));
  const autosave = useAutosave({ onSave: (value) => onSave(parseRoles(value)) });

  return (
    <SectionShell
      title="open roles"
      status={autosave.status}
      onBlur={() => {
        void autosave.flush(text);
      }}
    >
      <Textarea
        label="open roles"
        hint="one role per line"
        rows={5}
        value={text}
        onChange={(e) => {
          setText(e.target.value);
          autosave.schedule(e.target.value);
        }}
      />
    </SectionShell>
  );
}

export default function SpeechTemplateScreen() {
  const { data, isPending, isError } = useSpeechTemplate();
  const update = useUpdateSpeechTemplate();

  if (isPending) return <ContentLoading />;
  if (isError) return <ContentError message="couldn't load the speech template — try refreshing" />;

  return (
    <ContentContainer>
      <h1 className="mb-2 text-2xl font-medium tracking-tight">event speech</h1>
      <p className="text-foreground-tertiary mb-6 text-sm">
        use a blockquote for speaker notes — they show as asides and aren&apos;t read aloud. insert
        blanks with + blank; facilitators fill them in per event.
      </p>
      <div className="flex flex-col gap-8">
        <PmSection
          title="everyone hears this"
          initial={data.sharedPm}
          onSave={async (sharedPm) => {
            await update.mutateAsync({ sharedPm });
          }}
        />
        <PmSection
          title="walks only"
          initial={data.walkPm}
          onSave={async (walkPm) => {
            await update.mutateAsync({ walkPm });
          }}
        />
        <PmSection
          title="restaurants only"
          initial={data.restaurantPm}
          onSave={async (restaurantPm) => {
            await update.mutateAsync({ restaurantPm });
          }}
        />
        <OpenRolesSection
          initial={data.openRoles}
          onSave={async (openRoles) => {
            await update.mutateAsync({ openRoles });
          }}
        />
      </div>
    </ContentContainer>
  );
}
