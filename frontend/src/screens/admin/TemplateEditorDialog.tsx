import { Fragment, type ReactNode, type SyntheticEvent, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { cn } from '@/utils/cn';

const MAX_LENGTH = 4000;

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  description: ReactNode;
  placeholders: { name: string; hint?: string }[];
  ariaLabel: string;
  template: { body: string } | null;
  update: { mutateAsync: (body: string) => Promise<unknown>; isPending: boolean };
  noun?: string;
  rows?: number;
}

export function TemplateEditorDialog({ open, onClose, title, template, ...form }: Props) {
  if (!open) return null;
  // Keyed on the body so each open seeds fresh state without an effect.
  return (
    <Dialog open onClose={onClose} title={title}>
      <EditorForm
        key={template?.body ?? ''}
        initialBody={template?.body ?? ''}
        onClose={onClose}
        {...form}
      />
    </Dialog>
  );
}

type FormProps = Omit<Props, 'open' | 'title' | 'template'> & { initialBody: string };

function EditorForm({
  initialBody,
  onClose,
  description,
  placeholders,
  ariaLabel,
  update,
  noun = 'message',
  rows = 10,
}: FormProps) {
  const [body, setBody] = useState(initialBody);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (!body.trim()) {
      setFormError(`${ariaLabel} is required`);
      return;
    }
    try {
      await update.mutateAsync(body);
      toast.success(`${noun} saved 🌱`);
      onClose();
    } catch (err) {
      setFormError(extractApiErrorOr(err, `couldn't save the ${noun} — try again`));
    }
  }

  const overLimit = body.length > MAX_LENGTH;
  const nearLimit = body.length > MAX_LENGTH * 0.9;

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
      <p className="text-foreground-secondary text-sm">{description}</p>
      <p className="text-muted text-xs">
        available placeholders:{' '}
        {placeholders.map(({ name, hint }, i) => (
          <Fragment key={name}>
            {i > 0 ? ', ' : null}
            <code className="bg-surface-dim rounded px-1">{`\${${name}}`}</code>
            {hint ? ` (${hint})` : null}
          </Fragment>
        ))}
      </p>
      <textarea
        value={body}
        onChange={(e) => {
          setBody(e.target.value);
        }}
        rows={rows}
        className="border-border bg-background text-foreground focus-visible:ring-brand-200 w-full rounded-md border p-3 font-mono text-base focus-visible:ring-2 focus-visible:outline-none md:text-sm"
        aria-label={ariaLabel}
      />
      <div
        className={cn(
          'text-right text-xs',
          overLimit ? 'text-red-600' : nearLimit ? 'text-warning' : 'text-muted',
        )}
      >
        {body.length} / {MAX_LENGTH}
      </div>
      {formError ? (
        <p role="alert" className="text-sm text-red-600">
          {formError}
        </p>
      ) : null}
      <div className="mt-2 flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          cancel
        </Button>
        <Button type="submit" disabled={update.isPending || overLimit}>
          {update.isPending ? 'saving…' : 'save'}
        </Button>
      </div>
    </form>
  );
}
