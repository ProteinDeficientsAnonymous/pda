import { type SyntheticEvent, useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import { useUpdateWhatsAppLink, type WhatsAppLink } from '@/api/content';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';

const MAX_LENGTH = 200;

interface Props {
  open: boolean;
  onClose: () => void;
  whatsappLink: WhatsAppLink | null;
}

export function WhatsAppLinkEditorDialog({ open, onClose, whatsappLink }: Props) {
  if (!open) return null;
  return (
    <Dialog open onClose={onClose} title="edit whatsapp link">
      <EditorForm
        key={whatsappLink?.link ?? ''}
        initialLink={whatsappLink?.link ?? ''}
        onClose={onClose}
      />
    </Dialog>
  );
}

function EditorForm({ initialLink, onClose }: { initialLink: string; onClose: () => void }) {
  const update = useUpdateWhatsAppLink();
  const [link, setLink] = useState(initialLink);
  const [formError, setFormError] = useState<string | null>(null);

  async function onSubmit(e: SyntheticEvent) {
    e.preventDefault();
    setFormError(null);
    try {
      await update.mutateAsync(link.trim());
      toast.success('whatsapp link saved 🌱');
      onClose();
    } catch (err) {
      setFormError(extractApiErrorOr(err, "couldn't save the link — try again"));
    }
  }

  const overLimit = link.length > MAX_LENGTH;

  return (
    <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-3">
      <p className="text-foreground-secondary text-sm">
        used as the <code className="bg-surface-dim rounded px-1">{'${WHATSAPP_LINK}'}</code>{' '}
        placeholder in the welcome and tentative approval messages.
      </p>
      <input
        type="text"
        value={link}
        onChange={(e) => {
          setLink(e.target.value);
        }}
        placeholder="https://chat.whatsapp.com/…"
        className="border-border bg-background text-foreground focus-visible:ring-brand-200 w-full rounded-md border p-3 font-mono text-sm focus-visible:ring-2 focus-visible:outline-none"
        aria-label="whatsapp link"
      />
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
