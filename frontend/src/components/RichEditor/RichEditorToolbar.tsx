import type { Editor } from '@tiptap/react';
import { useEffect, useRef, useState } from 'react';
import { cn } from '@/utils/cn';
import { CtaDialog } from './CtaDialog';
import type { CtaAttrs } from './CtaExtension';

interface Props {
  editor: Editor;
}

type HeadingLevel = 1 | 2 | 3;
type Alignment = 'left' | 'center' | 'right';

export function RichEditorToolbar({ editor }: Props) {
  const [ctaOpen, setCtaOpen] = useState(false);
  const ctaActive = editor.isActive('cta');
  const ctaInitial: CtaAttrs | null = ctaActive ? (editor.getAttributes('cta') as CtaAttrs) : null;

  return (
    <div
      role="toolbar"
      aria-label="formatting"
      className="border-border flex flex-wrap items-center gap-0.5 border-b px-1.5 py-1.5"
    >
      <ToolButton
        label="bold"
        active={editor.isActive('bold')}
        onClick={() => editor.chain().focus().toggleBold().run()}
      >
        <IconBold />
      </ToolButton>
      <ToolButton
        label="italic"
        active={editor.isActive('italic')}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      >
        <IconItalic />
      </ToolButton>
      <ToolButton
        label="code"
        active={editor.isActive('code')}
        onClick={() => editor.chain().focus().toggleCode().run()}
      >
        <IconCode />
      </ToolButton>
      <Divider />
      <HeadingMenu editor={editor} />
      <ListMenu editor={editor} />
      <AlignMenu editor={editor} />
      <Divider />
      <ToolButton
        label="add link"
        active={editor.isActive('link')}
        onClick={() => {
          promptLink(editor);
        }}
      >
        <IconLink />
      </ToolButton>
      <ToolButton
        label="blockquote"
        active={editor.isActive('blockquote')}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      >
        <IconQuote />
      </ToolButton>
      <ToolButton
        label="button"
        active={ctaActive}
        onClick={() => {
          setCtaOpen(true);
        }}
      >
        <span className="text-xs">button</span>
      </ToolButton>
      <CtaDialog
        open={ctaOpen}
        initial={ctaInitial}
        onClose={() => {
          setCtaOpen(false);
        }}
        onSubmit={(attrs) => {
          if (ctaActive) editor.chain().focus().updateCta(attrs).run();
          else editor.chain().focus().insertCta(attrs).run();
          setCtaOpen(false);
        }}
      />
    </div>
  );
}

function HeadingMenu({ editor }: { editor: Editor }) {
  const activeLevel = ([1, 2, 3] as HeadingLevel[]).find((l) =>
    editor.isActive('heading', { level: l }),
  );
  return (
    <Menu
      label="heading"
      active={activeLevel !== undefined}
      trigger={<span className="text-xs">{activeLevel ? `h${String(activeLevel)}` : 'text'}</span>}
    >
      {(close) => (
        <>
          <MenuItem
            active={!activeLevel}
            onClick={() => {
              editor.chain().focus().setParagraph().run();
              close();
            }}
          >
            text
          </MenuItem>
          {([1, 2, 3] as HeadingLevel[]).map((level) => (
            <MenuItem
              key={level}
              active={activeLevel === level}
              onClick={() => {
                editor.chain().focus().toggleHeading({ level }).run();
                close();
              }}
            >
              h{level}
            </MenuItem>
          ))}
        </>
      )}
    </Menu>
  );
}

function ListMenu({ editor }: { editor: Editor }) {
  const isBullet = editor.isActive('bulletList');
  const isOrdered = editor.isActive('orderedList');
  return (
    <Menu
      label="list"
      active={isBullet || isOrdered}
      trigger={isOrdered ? <IconOrderedList /> : <IconBulletList />}
    >
      {(close) => (
        <>
          <MenuItem
            active={isBullet}
            onClick={() => {
              editor.chain().focus().toggleBulletList().run();
              close();
            }}
          >
            <IconBulletList />
            <span className="ml-2">bullets</span>
          </MenuItem>
          <MenuItem
            active={isOrdered}
            onClick={() => {
              editor.chain().focus().toggleOrderedList().run();
              close();
            }}
          >
            <IconOrderedList />
            <span className="ml-2">numbered</span>
          </MenuItem>
        </>
      )}
    </Menu>
  );
}

function AlignMenu({ editor }: { editor: Editor }) {
  const current: Alignment =
    (['center', 'right'] as Alignment[]).find((a) => editor.isActive({ textAlign: a })) ?? 'left';
  return (
    <Menu
      label="text alignment"
      active={current !== 'left'}
      trigger={<AlignIcon alignment={current} />}
    >
      {(close) => (
        <>
          {(['left', 'center', 'right'] as Alignment[]).map((a) => (
            <MenuItem
              key={a}
              active={current === a}
              onClick={() => {
                editor.chain().focus().setTextAlign(a).run();
                close();
              }}
            >
              <AlignIcon alignment={a} />
              <span className="ml-2">{a}</span>
            </MenuItem>
          ))}
        </>
      )}
    </Menu>
  );
}

function Menu({
  label,
  trigger,
  active,
  children,
}: {
  label: string;
  trigger: React.ReactNode;
  active: boolean;
  children: (close: () => void) => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onMouseDown={(e) => {
          e.preventDefault();
        }}
        onClick={() => {
          setOpen((o) => !o);
        }}
        className={cn(
          'hover:bg-surface-dim flex h-8 items-center gap-0.5 rounded px-1.5 text-sm transition-colors',
          active && 'bg-surface-raised text-foreground',
        )}
      >
        {trigger}
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="h-3 w-3"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8l4 4 4-4" />
        </svg>
      </button>
      {open ? (
        <div className="border-border-strong bg-surface absolute top-full left-0 z-20 mt-1 min-w-[8rem] rounded-md border p-1 shadow-md">
          {children(() => {
            setOpen(false);
          })}
        </div>
      ) : null}
    </div>
  );
}

function MenuItem({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="menuitem"
      onMouseDown={(e) => {
        e.preventDefault();
      }}
      onClick={onClick}
      className={cn(
        'hover:bg-surface-dim flex w-full items-center rounded px-2 py-1 text-left text-sm transition-colors',
        active && 'bg-surface-raised text-foreground',
      )}
    >
      {children}
    </button>
  );
}

function Divider() {
  return <span aria-hidden="true" className="bg-surface-raised mx-1 h-5 w-px" />;
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
      onMouseDown={(e) => {
        e.preventDefault();
      }}
      onClick={onClick}
      className={cn(
        'hover:bg-surface-dim flex h-8 min-w-8 items-center justify-center rounded px-1.5 text-sm transition-colors',
        active && 'bg-surface-raised text-foreground',
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

// --- icons ---

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 20 20"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

function IconBold() {
  return (
    <Icon>
      <path d="M6 4h5a3 3 0 010 6H6zM6 10h6a3 3 0 010 6H6z" />
    </Icon>
  );
}

function IconItalic() {
  return (
    <Icon>
      <path d="M12 4l-4 12M8 4h6M6 16h6" />
    </Icon>
  );
}

function IconCode() {
  return (
    <Icon>
      <path d="M7 6l-4 4 4 4M13 6l4 4-4 4" />
    </Icon>
  );
}

function IconBulletList() {
  return (
    <Icon>
      <circle cx="4" cy="6" r="0.75" fill="currentColor" />
      <circle cx="4" cy="10" r="0.75" fill="currentColor" />
      <circle cx="4" cy="14" r="0.75" fill="currentColor" />
      <path d="M8 6h10M8 10h10M8 14h10" />
    </Icon>
  );
}

function IconOrderedList() {
  return (
    <Icon>
      <path d="M8 6h10M8 10h10M8 14h10" />
      <path d="M3 4v4M2 8h2M2 12h2l-2 2h2" strokeWidth="1.25" />
    </Icon>
  );
}

function IconLink() {
  return (
    <Icon>
      <path d="M9 11a3 3 0 004 0l3-3a3 3 0 00-4-4l-1 1" />
      <path d="M11 9a3 3 0 00-4 0l-3 3a3 3 0 004 4l1-1" />
    </Icon>
  );
}

function IconQuote() {
  return (
    <Icon>
      <path d="M6 6c-2 0-3 2-3 4v4h4v-4H5c0-2 1-3 2-3zM14 6c-2 0-3 2-3 4v4h4v-4h-2c0-2 1-3 2-3z" />
    </Icon>
  );
}

function AlignIcon({ alignment }: { alignment: Alignment }) {
  return (
    <Icon>
      {alignment === 'left' ? (
        <path d="M3 5h14M3 9h10M3 13h14M3 17h10" />
      ) : alignment === 'center' ? (
        <path d="M3 5h14M5 9h10M3 13h14M5 17h10" />
      ) : (
        <path d="M3 5h14M7 9h10M3 13h14M7 17h10" />
      )}
    </Icon>
  );
}
