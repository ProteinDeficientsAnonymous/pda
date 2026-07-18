import { useState } from 'react';

import { useAutosave } from '@/hooks/useAutosave';

import { AutosaveStatus } from './AutosaveStatus';
import { HtmlContent } from './HtmlContent';
import { RichEditor } from './RichEditor/RichEditor';
import { Button } from './ui/Button';

interface Props {
  canEdit: boolean;
  contentHtml: string;
  initialPm: string;
  onSave: (contentPm: string) => Promise<void>;
  placeholder?: string;
  toolbar?: 'inline' | 'none';
}

export function EditableHtmlBlock({
  canEdit,
  contentHtml,
  initialPm,
  onSave,
  placeholder,
  toolbar = 'inline',
}: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(initialPm);
  const autosave = useAutosave({ onSave });

  function handleChange(next: string) {
    setDraft(next);
    autosave.schedule(next);
  }

  async function stopEditing() {
    if (draft !== initialPm) await autosave.flush(draft);
    setEditing(false);
  }

  if (!canEdit) return <HtmlContent html={contentHtml} />;

  if (!editing) {
    return (
      <div className="relative">
        {toolbar === 'inline' ? (
          <div className="mb-2 flex justify-end">
            <Button
              variant="ghost"
              onClick={() => {
                setDraft(initialPm);
                setEditing(true);
              }}
            >
              edit
            </Button>
          </div>
        ) : null}
        <HtmlContent html={contentHtml} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <div className="flex-1">
          <AutosaveStatus status={autosave.status} />
        </div>
        <Button variant="ghost" onClick={() => void stopEditing()}>
          done
        </Button>
      </div>
      <RichEditor value={draft} onChange={handleChange} placeholder={placeholder} />
    </div>
  );
}
