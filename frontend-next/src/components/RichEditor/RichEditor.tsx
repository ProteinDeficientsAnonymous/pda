// TipTap editor wrapper. Serializes to ProseMirror JSON strings (not
// JSObjects) to match the backend wire format — the content_pm column is a
// TextField, not a JSONField.

import { useEditor, EditorContent, type JSONContent } from '@tiptap/react';
import { useEffect } from 'react';
import { pdaExtensions } from './tiptapConfig';
import { RichEditorToolbar } from './RichEditorToolbar';
import { cn } from '@/utils/cn';

interface Props {
  /** ProseMirror JSON as a string. Empty string → start blank. */
  value: string;
  onChange: (value: string) => void;
  placeholder?: string | undefined;
  className?: string | undefined;
  disabled?: boolean;
}

function parseValue(value: string): JSONContent | null {
  if (!value.trim()) return null;
  try {
    return JSON.parse(value) as JSONContent;
  } catch {
    return null;
  }
}

export function RichEditor({ value, onChange, placeholder, className, disabled }: Props) {
  const editor = useEditor({
    extensions: pdaExtensions(),
    content: parseValue(value),
    editable: !disabled,
    editorProps: {
      attributes: {
        class:
          'min-h-[200px] rounded-b-md px-3 py-2 outline-none prose prose-neutral max-w-none focus:ring-2 focus:ring-neutral-200',
        'aria-label': placeholder ?? 'editor',
      },
    },
    onUpdate: ({ editor: e }) => {
      onChange(JSON.stringify(e.getJSON()));
    },
  });

  // Keep the editor editable flag in sync with the disabled prop.
  useEffect(() => {
    editor.setEditable(!disabled);
  }, [editor, disabled]);

  return (
    <div className={cn('rounded-md border border-neutral-300 bg-white', className)}>
      <RichEditorToolbar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
}
