import { type SyntheticEvent, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { type MemberPromotionMessage, useUpdateMemberPromotionMessage } from '@/api/content';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { cn } from '@/utils/cn';

const MAX_LENGTH = 4000;

interface Props {
  open: boolean;
  onClose: () => void;
  template: MemberPromotionMessage | null;
}

export function MemberPromotionMessageEditorDialog({ open, onClose, template }: Props) {
  if (!open) return null;
  // Inner form is keyed on the template body so each open seeds fresh state
  // without an effect.
  return (
    <Dialog open onClose={onClose} title="edit member promotion message">
      <EditorForm key={template?.body ?? ''} initialBody={template?.body ?? ''} onClose={onClose} />
    </Dialog>
  );
}

function EditorForm({ initialBody, onClose }: { initialBody: string; onClose: () => void }) {
  const update = useUpdateMemberPromotionMessage();
  const [body, setBody] = useState(initialBody);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    if (!body.trim()) {
      setFormError('message body is required');
      return;
    }
    try {
      await update.mutateAsync(body);
      toast.success('message saved 🌱');
      onClose();
    } catch (err) {
      setFormError(extractApiErrorOr(err, "couldn't save the message — try again"));
    }
  }

  const overLimit = body.length > MAX_LENGTH;
  const nearLimit = body.length > MAX_LENGTH * 0.9;

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
      <p className="text-foreground-secondary text-sm">
        sent when a tentatively-approved applicant is manually promoted to full member — this
        replaces the default message text.
      </p>
      <p className="text-muted text-xs">
        available placeholders:{' '}
        <code className="bg-surface-dim rounded px-1">{'${FIRST_NAME}'}</code> (recipient's first
        name), <code className="bg-surface-dim rounded px-1">{'${SENDER_NAME}'}</code>,{' '}
        <code className="bg-surface-dim rounded px-1">{'${MAGIC_LINK}'}</code>,{' '}
        <code className="bg-surface-dim rounded px-1">{'${WHATSAPP_LINK}'}</code>
      </p>
      <textarea
        value={body}
        onChange={(e) => {
          setBody(e.target.value);
        }}
        rows={10}
        className="border-border bg-background text-foreground focus-visible:ring-brand-200 w-full rounded-md border p-3 font-mono text-base focus-visible:ring-2 focus-visible:outline-none md:text-sm"
        aria-label="member promotion message body"
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
