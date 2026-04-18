import type { Editor } from '@tiptap/react';
import { cn } from '@/utils/cn';

interface Props {
  editor: Editor;
}

export function RichEditorToolbar({ editor }: Props) {
  return (
    <div
      role="toolbar"
      aria-label="formatting"
      className="flex flex-wrap items-center gap-1 border-b border-neutral-200 px-2 py-1.5"
    >
      <ToolButton
        label="bold"
        active={editor.isActive('bold')}
        onClick={() => editor.chain().focus().toggleBold().run()}
      >
        <strong>B</strong>
      </ToolButton>
      <ToolButton
        label="italic"
        active={editor.isActive('italic')}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      >
        <em>I</em>
      </ToolButton>
      <ToolButton
        label="code"
        active={editor.isActive('code')}
        onClick={() => editor.chain().focus().toggleCode().run()}
      >
        <code>{'</>'}</code>
      </ToolButton>
      <Divider />
      <ToolButton
        label="heading 1"
        active={editor.isActive('heading', { level: 1 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
      >
        H1
      </ToolButton>
      <ToolButton
        label="heading 2"
        active={editor.isActive('heading', { level: 2 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
      >
        H2
      </ToolButton>
      <ToolButton
        label="heading 3"
        active={editor.isActive('heading', { level: 3 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
      >
        H3
      </ToolButton>
      <Divider />
      <ToolButton
        label="bullet list"
        active={editor.isActive('bulletList')}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      >
        • list
      </ToolButton>
      <ToolButton
        label="numbered list"
        active={editor.isActive('orderedList')}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      >
        1. list
      </ToolButton>
      <Divider />
      <ToolButton
        label="add link"
        active={editor.isActive('link')}
        onClick={() => {
          promptLink(editor);
        }}
      >
        link
      </ToolButton>
      <ToolButton
        label="blockquote"
        active={editor.isActive('blockquote')}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      >
        &ldquo; &rdquo;
      </ToolButton>
    </div>
  );
}

function Divider() {
  return <span aria-hidden="true" className="mx-1 h-5 w-px bg-neutral-200" />;
}

function ToolButton({
  label,
  active,
  onClick,
  children,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        'h-8 rounded px-2 text-sm transition-colors hover:bg-neutral-100',
        active && 'bg-neutral-200 text-neutral-900',
      )}
    >
      {children}
    </button>
  );
}

function promptLink(editor: Editor) {
  const previous = (editor.getAttributes('link').href as string | undefined) ?? '';
  const url = window.prompt('url', previous);
  if (url === null) return;
  if (url === '') {
    editor.chain().focus().extendMarkRange('link').unsetLink().run();
    return;
  }
  editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
}
