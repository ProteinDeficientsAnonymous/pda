// Sub-modal opened from ApprovalCredentialsDialog. Lets users with
// EDIT_WELCOME_MESSAGE edit the shared template. Plain-text only —
// placeholders ${NAME}, ${SENDER_NAME}, ${MAGIC_LINK} are substituted at
// render time by renderWelcomeMessage().

import { useState, type SyntheticEvent } from 'react';
import { toast } from 'sonner';
import { extractApiErrorOr } from '@/api/apiErrors';
import { useUpdateWelcomeTemplate, type WelcomeTemplate } from '@/api/content';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { cn } from '@/utils/cn';

const MAX_LENGTH = 4000;

interface Props {
  open: boolean;
  onClose: () => void;
  template: WelcomeTemplate | null;
}

export function WelcomeTemplateEditorDialog({ open, onClose, template }: Props) {
  if (!open) return null;
  // Inner form is keyed on the template body so each open seeds fresh state
  // without an effect.
  return (
    <Dialog open onClose={onClose} title="edit welcome message">
      <EditorForm key={template?.body ?? ''} initialBody={template?.body ?? ''} onClose={onClose} />
    </Dialog>
  );
}

function EditorForm({ initialBody, onClose }: { initialBody: string; onClose: () => void }) {
  const update = useUpdateWelcomeTemplate();
  const [body, setBody] = useState(initialBody);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (!body.trim()) {
      setFormError('welcome message body is required');
      return;
    }
    try {
      await update.mutateAsync(body);
      toast.success('template saved 🌱');
      onClose();
    } catch (err) {
      setFormError(extractApiErrorOr(err, "couldn't save template — try again"));
    }
  }

  const overLimit = body.length > MAX_LENGTH;
  const nearLimit = body.length > MAX_LENGTH * 0.9;

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
      <p className="text-foreground-secondary text-sm">
        this text is shared with all vetters. changes apply everywhere.
      </p>
      <p className="text-muted text-xs">
        available placeholders: <code className="bg-surface-dim rounded px-1">{'${NAME}'}</code>,{' '}
        <code className="bg-surface-dim rounded px-1">{'${SENDER_NAME}'}</code>,{' '}
        <code className="bg-surface-dim rounded px-1">{'${MAGIC_LINK}'}</code>
      </p>
      <textarea
        value={body}
        onChange={(e) => {
          setBody(e.target.value);
        }}
        rows={14}
        className="border-border bg-background text-foreground focus-visible:ring-brand-200 w-full rounded-md border p-3 font-mono text-sm focus-visible:ring-2 focus-visible:outline-none"
        aria-label="welcome message body"
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
