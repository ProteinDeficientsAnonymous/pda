// View-or-edit content block. Non-editors see the sanitized HTML. Users with
// the right permission see an "edit" toggle that swaps to a TipTap editor
// with autosave. The component doesn't own the data — callers pass both the
// current values and the save callback, so home/faq/guidelines/editable pages
// can all reuse it.

import { useState } from 'react';
import { RichEditor } from './RichEditor/RichEditor';
import { HtmlContent } from './HtmlContent';
import { AutosaveStatus } from './AutosaveStatus';
import { Button } from './ui/Button';
import { useAutosave } from '@/hooks/useAutosave';

interface Props {
  canEdit: boolean;
  contentHtml: string;
  /** ProseMirror JSON string to seed the editor. Empty string = blank doc. */
  initialPm: string;
  onSave: (contentPm: string) => Promise<void>;
  placeholder?: string;
  /**
   * Whether to show the "edit" chip inline with the rendered content, or
   * leave the caller to place it elsewhere. Defaults to inline.
   */
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

  function stopEditing() {
    autosave.cancel();
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
      <div className="flex items-center justify-between">
        <AutosaveStatus status={autosave.status} />
        <Button variant="ghost" onClick={stopEditing}>
          done
        </Button>
      </div>
      <RichEditor value={draft} onChange={handleChange} placeholder={placeholder} />
    </div>
  );
}
