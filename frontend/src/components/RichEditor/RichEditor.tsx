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
        class: [
          'min-h-[200px] max-w-none rounded-b-md px-3 py-2 outline-none focus:ring-2 focus:ring-border',
          'text-foreground break-words [overflow-wrap:anywhere]',
          '[&_a]:text-foreground [&_a]:underline',
          '[&_h1]:mt-6 [&_h1]:mb-2 [&_h1]:text-2xl [&_h1]:font-medium',
          '[&_h2]:mt-5 [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-medium',
          '[&_h3]:mt-4 [&_h3]:mb-2 [&_h3]:text-lg [&_h3]:font-medium',
          '[&_p]:my-3',
          '[&_ul]:my-3 [&_ul]:list-disc [&_ul]:ps-6',
          '[&_ol]:my-3 [&_ol]:list-decimal [&_ol]:ps-6',
          '[&_blockquote]:border-border-strong [&_blockquote]:border-s-4 [&_blockquote]:ps-4 [&_blockquote]:italic',
          '[&_code]:bg-surface-dim [&_code]:rounded [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-sm',
          '[&_a.cta]:my-3 [&_a.cta]:inline-flex [&_a.cta]:h-10 [&_a.cta]:items-center [&_a.cta]:justify-center [&_a.cta]:rounded-md [&_a.cta]:px-4 [&_a.cta]:text-sm [&_a.cta]:font-medium [&_a.cta]:no-underline [&_a.cta]:cursor-pointer',
          '[&_a.cta--primary]:bg-brand-600 [&_a.cta--primary]:text-brand-on',
          '[&_a.cta--secondary]:bg-surface [&_a.cta--secondary]:text-foreground [&_a.cta--secondary]:border [&_a.cta--secondary]:border-border-strong',
          '[&_.ProseMirror-selectednode]:ring-2 [&_.ProseMirror-selectednode]:ring-brand-500',
        ].join(' '),
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
    <div className={cn('border-border-strong bg-surface rounded-md border', className)}>
      <RichEditorToolbar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
}
