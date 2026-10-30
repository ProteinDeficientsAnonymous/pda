import { useState } from 'react';

import { useSpeechTemplate, useUpdateSpeechTemplate } from '@/api/eventSpeech';
import { AutosaveStatus } from '@/components/AutosaveStatus';
import { Textarea } from '@/components/ui/Textarea';
import { useAutosave } from '@/hooks/useAutosave';
import { ContentContainer, ContentError, ContentLoading } from '@/screens/public/ContentContainer';

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
      <div className="flex flex-col gap-8">
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
